# =============================================================================
# URTC Flasher - CAN bootloader OTA protocol implementation (URTCFlasher),
# matching BOOTLOADER.C's own state machine exactly. Transport-agnostic -
# works with any object exposing send_frame/read_frame (SLCAN, SocketCAN,
# or MockCAN from flasher_transports.py).
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import hashlib
import hmac
import json
import os
import struct
import time
import zlib

from flasher_config import (
    _, APP_MAX_SIZE, CAN_ID_BOOTLOADER_VERSION_RESPONSE, CAN_ID_DATA,
    CAN_ID_END_UPDATE, CAN_ID_ENTER_BOOTLOADER, CAN_ID_ERASE_FRAM,
    CAN_ID_FRAM_STATE_RESP, CAN_ID_HEARTBEAT, CAN_ID_HMAC_CHUNK, CAN_ID_PAGE_ACK,
    CAN_ID_QUERY_VERSION, CAN_ID_START_UPDATE, CAN_ID_STATUS, CAN_ID_VERSION_RESPONSE,
    ERASE_FRAM_MAGIC, FIRMWARE_VERSION_MAJOR, FIRMWARE_VERSION_MINOR, FLASH_PAGE_SIZE,
    HMAC_KEY, STATUS_NAMES, THIS_HARDWARE_ID, VERIFY_FAIL_REASONS,
    CAN_ID_SLAVE_ENTER_BOOTLOADER, CAN_ID_SLAVE_START_UPDATE, CAN_ID_SLAVE_HMAC_CHUNK,
    CAN_ID_SLAVE_DATA, CAN_ID_SLAVE_END_UPDATE, CAN_ID_SLAVE_STATUS,
    CAN_ID_SLAVE_PROGRESS, CAN_ID_SLAVE_VERSION_RESP_1, CAN_ID_SLAVE_VERSION_RESP_2,
    SLAVE_HARDWARE_ID, SLAVE_APP_MAX_SIZE,
)

class FlashError(Exception):
    pass


class URTCFlasher:
    def __init__(self, slcan, log, progress_cb=None, stop_flag=None):
        self.can = slcan
        self.log = log
        self.progress_cb = progress_cb or (lambda pct: None)
        self.stop_flag = stop_flag or (lambda: False)
        self._last_heartbeat_pct = None  # tracked across _wait_for calls for the page-ACK retry's active confirmation check

    def query_version(self, timeout=1.5):
        """Asks whatever's currently running (application or bootloader)
        to identify itself. Returns a dict with keys: responder ('application'
        or 'bootloader'), hardware_id, version_major, version_minor, and
        bootloader_version (a (major, minor, patch) tuple, or None) - or
        None if nothing answered within the timeout (board unresponsive,
        wrong bitrate, not connected, etc.).

        bootloader_version only ever gets filled in when the BOOTLOADER is
        the one answering (responder == 'bootloader') - it comes from a
        separate 0x7FA frame the bootloader sends right alongside 0x7F9,
        which the running application never sends (it has no way to know
        a currently-flashed bootloader's version other than this). A short
        grace window after 0x7F9 arrives catches 0x7FA even though the two
        aren't guaranteed to land within the same read_frame() call.
        """
        self.can.send_frame(CAN_ID_QUERY_VERSION, b"\x00")
        deadline = time.time() + timeout
        result = None
        grace_deadline = None
        pending_bootloader_version = None  # in case 0x7FA arrives before 0x7F9
        while time.time() < deadline:
            if result is not None and grace_deadline is not None and time.time() >= grace_deadline:
                return result  # got 0x7F9, grace window for 0x7FA expired with nothing more
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_VERSION_RESPONSE and len(data) == 8 and result is None:
                responder = "application" if data[0] == 0x00 else "bootloader"
                hw_id = struct.unpack(">I", data[1:5])[0]
                ver_major = struct.unpack(">H", data[5:7])[0]
                ver_minor = data[7]
                result = {
                    "responder": responder,
                    "hardware_id": hw_id,
                    "version_major": ver_major,
                    "version_minor": ver_minor,
                    "bootloader_version": pending_bootloader_version,
                }
                if responder != "bootloader":
                    return result  # application never sends 0x7FA - no point waiting for it
                if pending_bootloader_version is not None:
                    return result  # 0x7FA already arrived first - no need for the grace window
                grace_deadline = time.time() + 0.3
            elif can_id == CAN_ID_BOOTLOADER_VERSION_RESPONSE and len(data) == 3:
                if result is not None:
                    result["bootloader_version"] = (data[0], data[1], data[2])
                    return result
                # 0x7F9 hasn't arrived yet - hold onto this until it does,
                # rather than discarding it just because of arrival order.
                pending_bootloader_version = (data[0], data[1], data[2])
        return result

    def _wait_for(self, expected_id, timeout=2.0, expected_status_value=None):
        """Wait for a specific CAN ID, logging heartbeats/status seen along
        the way but not treating them as the answer unless they match.
        expected_status_value, when given (only meaningful alongside
        expected_id=CAN_ID_STATUS), additionally requires data[0] to equal
        that value before returning - otherwise a status frame carrying a
        different, intermediate value (e.g. STATUS_ERASING arriving before
        the STATUS_RECEIVING a caller actually needs) would be accepted as
        the answer just because the CAN ID matched."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.stop_flag():
                raise FlashError("Cancelled by user")
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_HEARTBEAT and len(data) == 2:
                status, pct = data[0], data[1]
                name = STATUS_NAMES.get(status, f"0x{status:02X}")
                pct_str = f"{pct}%" if pct != 0xFF else "--"
                self.log(_("LOG_HEARTBEAT", name=name, pct=pct_str))
                if pct != 0xFF:
                    self._last_heartbeat_pct = pct
            elif can_id == CAN_ID_STATUS and len(data) in (1, 2):
                name = STATUS_NAMES.get(data[0], f"0x{data[0]:02X}")
                if len(data) == 2 and data[0] == 0x05:  # STATUS_VERIFY_FAIL + reason byte
                    reason = VERIFY_FAIL_REASONS.get(data[1], f"unknown reason 0x{data[1]:02X}")
                    self.log(_("LOG_STATUS_WITH_REASON", name=name, reason=reason))
                else:
                    self.log(_("LOG_STATUS_NAME_ONLY", name=name))
                if can_id == expected_id and (expected_status_value is None or data[0] == expected_status_value):
                    return data
                # A genuine error status (not just an intermediate one the
                # caller isn't specifically waiting for) means the
                # bootloader already reported exactly what went wrong -
                # sitting through the rest of this timeout to eventually
                # raise a generic "Timed out" message would hide that
                # known cause instead of surfacing it immediately.
                if data[0] == 0x05:
                    reason = VERIFY_FAIL_REASONS.get(data[1], "unknown reason") if len(data) == 2 else "unknown reason"
                    raise FlashError(f"Bootloader reported verification failure: {reason}")
                if data[0] == 0xFF:
                    raise FlashError("Bootloader reported a generic error status")
                continue  # a status frame that didn't match - keep waiting, don't fall through to the generic check below
            if can_id == expected_id:
                return data
        raise FlashError(f"Timed out waiting for CAN ID 0x{expected_id:03X}")

    def erase_fram(self):
        """Sends 0x192 (magic-payload erase) to a currently-running
        application, wiping the persistence F-RAM's saved state. Only
        the application handles this - the bootloader doesn't - so this
        has to run before trigger_bootloader_entry(), not after. A missing
        confirmation is logged, not raised - this is a secondary, optional
        step alongside the actual firmware update, and losing just the
        confirmation frame shouldn't abort the whole flash the way a
        genuine protocol failure in flash() itself should."""
        self.log(_("LOG_ERASING_FRAM"))
        self.can.send_frame(CAN_ID_ERASE_FRAM, ERASE_FRAM_MAGIC)
        try:
            self._wait_for(CAN_ID_FRAM_STATE_RESP, timeout=2.0)
            self.log(_("LOG_FRAM_ERASE_CONFIRMED"))
        except FlashError:
            self.log(_("LOG_FRAM_ERASE_NO_CONFIRM_CONTINUING"))

    def trigger_bootloader_entry(self):
        """Sends 0x7F0 to a currently-running application to make it reset
        into the bootloader. Skip this if the board is already sitting in
        the bootloader (fresh JTAG flash, or no valid application present)."""
        self.log(_("LOG_SENDING_BOOTLOADER_TRIGGER"))
        self.can.send_frame(CAN_ID_ENTER_BOOTLOADER, bytes([0xB0, 0x07, 0x1D, 0x5A]))
        time.sleep(0.8)  # give the app time to shut down actuators and reset

    def _check_manifest(self, firmware_path, actual_sha256):
        manifest_path = firmware_path + ".manifest.json"
        if not os.path.isfile(manifest_path):
            return
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.log(_("LOG_MANIFEST_UNREADABLE", e=e))
            return

        # str() before .lower(): manifest.get() only supplies the ""
        # default when the key is absent - if it's present but the wrong
        # JSON type (null, or a bare number instead of a hex string),
        # .lower() on that would raise AttributeError, uncaught since this
        # line is outside the try/except above (which only covers the
        # JSON read/parse itself, not validating the values inside it).
        expected_sha256 = str(manifest.get("sha256", "") or "").lower().replace("0x", "")
        version = manifest.get("version", "?")
        build_date = manifest.get("build_date", "?")
        self.log(_("LOG_MANIFEST_INFO", version=version, build_date=build_date))
        if not expected_sha256:
            self.log(_("LOG_MANIFEST_NO_SHA256_FIELD"))
            return
        if expected_sha256 == actual_sha256.lower():
            self.log(_("LOG_MANIFEST_SHA256_MATCHES"))
        else:
            self.log(
                f"  ** MANIFEST MISMATCH ** - manifest.json declares sha256={expected_sha256}, "
                f"this file's actual sha256={actual_sha256}. This could mean the wrong file was "
                f"selected, the file was modified/corrupted after the manifest was written, or "
                f"the manifest itself is stale. Proceeding anyway - this check is a convenience "
                f"warning, not an authoritative gate the way the bootloader's own HMAC "
                f"verification is."
            )

    def flash(self, firmware_path):
        self._last_heartbeat_pct = None  # a stale value from a prior flash()
        # call in this same session would otherwise always satisfy the
        # page-ACK retry's ">=" check below, regardless of this update's
        # actual progress.
        with open(firmware_path, "rb") as f:
            firmware = f.read()

        size = len(firmware)
        if size == 0:
            raise FlashError("Firmware file is empty")
        if size > APP_MAX_SIZE:
            raise FlashError(
                f"Firmware is {size} bytes, exceeds the {APP_MAX_SIZE}-byte "
                f"main slot - refusing to send an update the bootloader "
                f"would reject anyway"
            )

        crc32 = zlib.crc32(firmware) & 0xFFFFFFFF
        signature = hmac.new(HMAC_KEY, firmware, hashlib.sha256).digest()
        actual_sha256 = hashlib.sha256(firmware).hexdigest()

        self.log(_("LOG_FIRMWARE_PATH", path=firmware_path))
        self.log(_("LOG_FIRMWARE_SIZE", size=size, kb=size/1024))
        self.log(_("LOG_FIRMWARE_CRC32", crc32=crc32))
        self.log(_("LOG_FIRMWARE_HMAC", hmac=signature.hex()))
        self.log(_("LOG_FIRMWARE_HARDWAREID", hw_id=THIS_HARDWARE_ID))

        self._check_manifest(firmware_path, actual_sha256)

        # --- 0x7F1: start update (size + HardwareID) ---
        self.log(_("LOG_SENDING_START_UPDATE"))
        payload = struct.pack(">II", size, THIS_HARDWARE_ID)
        self.can.send_frame(CAN_ID_START_UPDATE, payload)
        self._wait_for(CAN_ID_STATUS, timeout=5.0, expected_status_value=0x03)  # STATUS_RECEIVING specifically - not just STATUS_ERASING, which arrives first but before the (up to ~2s) erase has actually finished

        # --- 0x7F7 x4: HMAC signature chunks ---
        self.log(_("LOG_SENDING_HMAC"))
        for i in range(4):
            chunk = signature[i*8:(i+1)*8]
            self.can.send_frame(CAN_ID_HMAC_CHUNK, chunk)
            time.sleep(0.01)

        # --- 0x7F2: firmware data, page by page, waiting for each page ACK ---
        self.log(_("LOG_SENDING_FIRMWARE_DATA"))
        total_pages = (size + FLASH_PAGE_SIZE - 1) // FLASH_PAGE_SIZE
        offset = 0
        page_index = 0
        transfer_start = time.time()
        total_retries = 0
        while offset < size:
            if self.stop_flag():
                raise FlashError("Cancelled by user")
            page_start = time.time()
            page_end = min(offset + FLASH_PAGE_SIZE, size)
            page_data = firmware[offset:page_end]
            # send this page 8 bytes at a time
            for i in range(0, len(page_data), 8):
                chunk = page_data[i:i+8]
                self.can.send_frame(CAN_ID_DATA, chunk)
                time.sleep(0.001)  # small pacing gap - avoids overrunning the bootloader's own receive/flash-write pace
            # wait for this page's ACK before sending the next one - retries
            # the WAIT itself (not a resend of the page data) up to 2 extra
            # times with a short backoff, recovering from an ACK that was
            # delayed or lost on a noisy bus without the data itself being
            # lost. Deliberately doesn't resend the page's data on a
            # timeout: if the original data actually arrived fine and only
            # the ACK got lost, resending would make the bootloader read
            # those bytes as the start of the NEXT page, desyncing the
            # transfer - safely retrying the data itself would need the
            # bootloader to tolerate a duplicate page, which isn't
            # something this flasher-only change can verify or rely on.
            #
            # Each retry is more than a passive wait: the bootloader's own
            # heartbeat (already sent roughly once a second regardless)
            # reports its overall bytes-received as a percentage, which
            # this checks against what receiving this page in full would
            # imply - if they're consistent, that's real evidence the data
            # itself got through and only the ACK was lost on the way
            # back, rather than just waiting blind and hoping.
            expected_pct_after_this_page = int((page_end / size) * 100)
            ack = None
            last_err = None
            for attempt in range(3):
                if attempt > 0:
                    total_retries += 1
                    backoff = 0.3 * (2 ** (attempt - 1))  # 0.3s, then 0.6s
                    self.log(_("LOG_NO_ACK_RETRY", page=page_index, attempt=attempt+1))
                    time.sleep(backoff)
                try:
                    ack = self._wait_for(CAN_ID_PAGE_ACK, timeout=3.0)
                    last_err = None
                    break
                except FlashError as e:
                    last_err = e
                    if self._last_heartbeat_pct is not None and self._last_heartbeat_pct >= expected_pct_after_this_page:
                        self.log(_("LOG_HEARTBEAT_CONSISTENT_WITH_PAGE", pct=self._last_heartbeat_pct))
            if last_err is not None:
                raise last_err
            if len(ack) < 4:
                raise FlashError(
                    f"Page ACK for page {page_index} was only {len(ack)} bytes "
                    f"(expected at least 4) - likely bus noise corrupting the frame"
                )
            # Only the first 4 bytes carry the page index - a longer ack
            # (DLC padding from the CAN controller, not necessarily an
            # error) shouldn't crash struct.unpack, which requires exactly
            # 4 bytes.
            acked_page = struct.unpack(">I", ack[:4])[0]
            if acked_page != page_index:
                raise FlashError(
                    f"Page ACK mismatch: expected page {page_index}, "
                    f"bootloader acked page {acked_page}"
                )
            page_elapsed = time.time() - page_start
            page_kbps = (len(page_data) / 1024) / page_elapsed if page_elapsed > 0 else 0.0
            offset = page_end
            page_index += 1
            # Scaled to 0-70%, not 0-100% - the bootloader's own verify/copy
            # phase after this (see below) reports its own 0-100% via
            # heartbeat, which would otherwise make the bar visibly drop
            # back down right after reaching 100% here. Reserving the last
            # 30% for that phase keeps it monotonically increasing instead.
            pct = int((page_index / total_pages) * 70)
            self.progress_cb(pct)
            self.log(_("LOG_PAGE_WRITTEN_ACKED", page=page_index, total=total_pages,
                      elapsed=page_elapsed, kbps=page_kbps))

        transfer_elapsed = time.time() - transfer_start
        overall_kbps = (size / 1024) / transfer_elapsed if transfer_elapsed > 0 else 0.0
        retry_word = _("LBL_RETRY_SINGULAR") if total_retries == 1 else _("LBL_RETRY_PLURAL")
        self.log(_("LOG_TRANSFER_COMPLETE", size=size, elapsed=transfer_elapsed,
                  kbps=overall_kbps, retries=total_retries, retry_word=retry_word))

        # --- 0x7F4: end update (CRC32 + version) ---
        self.log(_("LOG_SENDING_END_UPDATE"))
        payload = struct.pack(">IHH", crc32, FIRMWARE_VERSION_MAJOR, FIRMWARE_VERSION_MINOR)
        self.can.send_frame(CAN_ID_END_UPDATE, payload)

        # The bootloader now verifies, then copies backup->main - this can
        # take several seconds for a large image (erase+write+read-back
        # verify per page). Watch for the final status.
        self.log(_("LOG_VERIFYING_COPYING_MAIN_SLOT"))
        deadline = time.time() + 60.0
        while time.time() < deadline:
            if self.stop_flag():
                raise FlashError("Cancelled by user")
            frame = self.can.read_frame(timeout=0.2)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_HEARTBEAT and len(data) == 2:
                status, pct = data[0], data[1]
                name = STATUS_NAMES.get(status, f"0x{status:02X}")
                pct_str = f"{pct}%" if pct != 0xFF else "--"
                self.log(_("LOG_HEARTBEAT", name=name, pct=pct_str))
                if pct != 0xFF:
                    self.progress_cb(70 + int(pct * 0.3))  # this phase owns the reserved 70-100% of the bar - see the comment on the page-transfer loop above
            elif can_id == CAN_ID_STATUS and len(data) in (1, 2):
                status = data[0]
                name = STATUS_NAMES.get(status, f"0x{status:02X}")
                if len(data) == 2 and status == 0x05:  # STATUS_VERIFY_FAIL + reason byte
                    reason = VERIFY_FAIL_REASONS.get(data[1], f"unknown reason 0x{data[1]:02X}")
                    self.log(_("LOG_STATUS_WITH_REASON", name=name, reason=reason))
                else:
                    self.log(_("LOG_STATUS_NAME_ONLY", name=name))
                if status == 0x04:
                    self.progress_cb(100)
                    self.log(_("LOG_UPDATE_VERIFIED_OK"))
                    return True
                elif status == 0x05 and len(data) == 2:
                    reason = VERIFY_FAIL_REASONS.get(data[1], f"unknown reason 0x{data[1]:02X}")
                    raise FlashError(f"Bootloader reported failure: {name} - {reason}")
                elif status in (0x05, 0xFF):
                    raise FlashError(f"Bootloader reported failure: {name}")
        # The confirmation frame itself (0x04) can be lost to the reset
        # transient even when the update genuinely succeeded - the board
        # already reset into new firmware, but that specific CAN frame
        # never made it out in time. Before declaring a hard failure,
        # check whether something now answers as the new application -
        # if so, the update did succeed, just without seeing its own
        # confirmation.
        self.log(_("LOG_NO_VERIFICATION_FRAME_CHECKING"))
        try:
            info = self.query_version(timeout=2.0)
        except Exception:
            info = None
        if info is not None and info.get("responder") == "application":
            self.progress_cb(100)
            self.log(_("LOG_BOARD_RESPONDING_AS_APP"))
            return True
        raise FlashError("Timed out waiting for final verification result")

    # -------------------------------------------------------------------
    # Expansion slave chip OTA - relayed through the main board's own
    # I2C bridge (CANBUS.TXT's own 0x210-0x218) rather than a direct CAN
    # peripheral on the slave chip, which has none. Same overall shape
    # as flash() above (enter bootloader, start, HMAC, data, end,
    # verify), but no page-ACK equivalent exists on this path - each
    # 0x213 write either completes or fails synchronously within that
    # same I2C transaction, so progress here comes from explicitly
    # polling 0x216 rather than an automatic heartbeat the bridge
    # doesn't send.
    # -------------------------------------------------------------------

    def trigger_slave_bootloader_entry(self):
        """Sends 0x210 (relayed to the slave's own application-mode
        REG_ENTER_BOOTLOADER) to make the expansion slave chip reset into
        its own bootloader. Skip this if it's already sitting there."""
        self.log(_("LOG_SENDING_SLAVE_BOOTLOADER_TRIGGER"))
        self.can.send_frame(CAN_ID_SLAVE_ENTER_BOOTLOADER, bytes([0xB0, 0x07, 0x1D, 0x5A]))
        time.sleep(0.8)  # same reset-transient allowance as the main board's own trigger_bootloader_entry()

    def query_slave_version(self, timeout=1.5):
        """Sends 0x217 (relayed to the slave bootloader's own version
        registers) and assembles the 2-frame response (0x217+0x218) into
        a dict. Returns None if the slave doesn't answer at all - no
        slave chip present (a Basic expansion board, or none), or it's
        currently mid-transfer and not listening for this query."""
        self.can.send_frame(CAN_ID_SLAVE_VERSION_RESP_1, b"")
        part1 = None
        part2 = None
        deadline = time.time() + timeout
        while time.time() < deadline and (part1 is None or part2 is None):
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_SLAVE_VERSION_RESP_1 and len(data) >= 8:
                part1 = data
            elif can_id == CAN_ID_SLAVE_VERSION_RESP_2 and len(data) >= 2:
                part2 = data
        if part1 is None or part2 is None:
            return None
        hw_id = struct.unpack(">I", part1[1:5])[0]
        app_major = struct.unpack(">H", part1[5:7])[0]
        app_minor = (part1[7] << 8) | part2[0]
        return {
            "responder": "bootloader" if part1[0] == 0x01 else "application",
            "hardware_id": hw_id,
            "app_version_major": app_major,
            "app_version_minor": app_minor,
            "bootloader_version": part2[1],
        }

    def flash_slave(self, firmware_path):
        """Same overall flow as flash() above, targeting the expansion
        slave chip instead - see this section's own header comment for
        the real protocol differences."""
        self._last_heartbeat_pct = None
        with open(firmware_path, "rb") as f:
            firmware = f.read()

        size = len(firmware)
        if size == 0:
            raise FlashError("Firmware file is empty")
        if size > SLAVE_APP_MAX_SIZE:
            raise FlashError(
                f"Firmware is {size} bytes, exceeds the expansion slave's own "
                f"{SLAVE_APP_MAX_SIZE}-byte main slot - refusing to send an "
                f"update its own bootloader would reject anyway"
            )

        crc32 = zlib.crc32(firmware) & 0xFFFFFFFF
        signature = hmac.new(HMAC_KEY, firmware, hashlib.sha256).digest()
        actual_sha256 = hashlib.sha256(firmware).hexdigest()

        self.log(_("LOG_FIRMWARE_PATH", path=firmware_path))
        self.log(_("LOG_FIRMWARE_SIZE", size=size, kb=size/1024))
        self.log(_("LOG_FIRMWARE_CRC32", crc32=crc32))
        self.log(_("LOG_FIRMWARE_HMAC", hmac=signature.hex()))
        self.log(_("LOG_SLAVE_FIRMWARE_HARDWAREID", hw_id=SLAVE_HARDWARE_ID))

        self._check_manifest(firmware_path, actual_sha256)

        # --- 0x211: start update (size + slave's own HardwareID) ---
        self.log(_("LOG_SENDING_SLAVE_START_UPDATE"))
        payload = struct.pack(">II", size, SLAVE_HARDWARE_ID)
        self.can.send_frame(CAN_ID_SLAVE_START_UPDATE, payload)
        self._wait_for_slave_status(0x03, timeout=5.0)  # STATUS_RECEIVING

        # --- 0x212 x4: HMAC signature chunks ---
        self.log(_("LOG_SENDING_HMAC"))
        for i in range(4):
            chunk = signature[i*8:(i+1)*8]
            self.can.send_frame(CAN_ID_SLAVE_HMAC_CHUNK, chunk)
            time.sleep(0.01)

        # --- 0x213: firmware data, 8 bytes per I2C transaction, no
        # page-ACK equivalent - each write either lands or the whole
        # relay is presumed gone (see the periodic 0x216 poll below for
        # how a stalled/absent slave is actually detected instead) ---
        self.log(_("LOG_SENDING_FIRMWARE_DATA"))
        transfer_start = time.time()
        offset = 0
        last_progress_check = 0
        while offset < size:
            if self.stop_flag():
                raise FlashError("Cancelled by user")
            chunk = firmware[offset:offset+8]
            self.can.send_frame(CAN_ID_SLAVE_DATA, chunk)
            offset += len(chunk)
            # Pacing gap wider than the main board's own 0x7F2 loop -
            # each frame here is its own I2C transaction on a bit-banged
            # bus, genuinely slower per-byte than the main board's own
            # direct flash write.
            time.sleep(0.004)

            # Poll progress roughly every 2KB rather than after every
            # single 8-byte frame - frequent enough to catch a stalled
            # transfer and update the progress bar smoothly, not so
            # frequent that the polling itself meaningfully slows down
            # the transfer.
            if offset - last_progress_check >= 2048 or offset >= size:
                last_progress_check = offset
                progress = self._query_slave_progress(timeout=0.5)
                pct = int((offset / size) * 70)  # same 0-70% reservation as the main board's own flow, see flash() above
                self.progress_cb(pct)
                if progress is not None:
                    self.log(_("LOG_SLAVE_PROGRESS", offset=offset, size=size, slave_pct=progress))

        transfer_elapsed = time.time() - transfer_start
        overall_kbps = (size / 1024) / transfer_elapsed if transfer_elapsed > 0 else 0.0
        self.log(_("LOG_SLAVE_TRANSFER_COMPLETE", size=size, elapsed=transfer_elapsed, kbps=overall_kbps))

        # --- 0x214: end update (CRC32 + version) - reusing this board's
        # own FIRMWARE_VERSION_MAJOR/MINOR here would be wrong (that's
        # this project's own main-board firmware version, not the
        # slave's own separate one) - the slave's own bootloader records
        # whatever version number this flash actually carries, taken
        # from the manifest if present, otherwise 0.0 (unknown) rather
        # than silently mislabeling it as the main board's own number. ---
        manifest_path = firmware_path + ".manifest.json"
        slave_major, slave_minor = 0, 0
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                version_str = str(manifest.get("version", "0.0"))
                parts = version_str.split(".")
                slave_major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
                slave_minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        self.log(_("LOG_SENDING_END_UPDATE"))
        payload = struct.pack(">IHH", crc32, slave_major, slave_minor)
        self.can.send_frame(CAN_ID_SLAVE_END_UPDATE, payload)

        # --- Watch 0x216 (progress) and 0x215 (status) until the copy
        # finishes or fails - same 60s allowance as the main board's own
        # flow, for the same reason (erase+write+read-back verify per
        # page on a much slower bit-banged I2C write than the main
        # board's own direct flash access). ---
        self.log(_("LOG_VERIFYING_COPYING_MAIN_SLOT"))
        deadline = time.time() + 60.0
        while time.time() < deadline:
            if self.stop_flag():
                raise FlashError("Cancelled by user")
            status = self._query_slave_status(timeout=1.0)
            if status is None:
                time.sleep(0.3)
                continue
            name = STATUS_NAMES.get(status, f"0x{status:02X}")
            self.log(_("LOG_STATUS_NAME_ONLY", name=name))
            if status == 0x04:  # STATUS_VERIFY_OK
                self.progress_cb(100)
                self.log(_("LOG_SLAVE_UPDATE_CONFIRMED"))
                return True
            if status == 0x05:  # STATUS_VERIFY_FAIL
                raise FlashError(_("LOG_SLAVE_VERIFY_FAILED"))
            if status == 0xFF:
                raise FlashError(_("LOG_SLAVE_GENERIC_ERROR"))
            progress = self._query_slave_progress(timeout=0.5)
            if progress is not None and progress != 0xFF:
                self.progress_cb(70 + int(progress * 0.3))
            time.sleep(0.3)
        raise FlashError("Timed out waiting for the expansion slave's own final verification result")

    def _query_slave_status(self, timeout=1.0):
        self.can.send_frame(CAN_ID_SLAVE_STATUS, b"")
        deadline = time.time() + timeout
        while time.time() < deadline:
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_SLAVE_STATUS and len(data) >= 1:
                return data[0]
        return None

    def _query_slave_progress(self, timeout=0.5):
        self.can.send_frame(CAN_ID_SLAVE_PROGRESS, b"")
        deadline = time.time() + timeout
        while time.time() < deadline:
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_SLAVE_PROGRESS and len(data) >= 1:
                return data[0]
        return None

    def _wait_for_slave_status(self, expected_value, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.stop_flag():
                raise FlashError("Cancelled by user")
            status = self._query_slave_status(timeout=0.5)
            if status == expected_value:
                return
            if status == 0xFF:
                raise FlashError(_("LOG_SLAVE_GENERIC_ERROR"))
            time.sleep(0.2)
        raise FlashError(f"Timed out waiting for the expansion slave to report status 0x{expected_value:02X}")



