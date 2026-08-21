# =============================================================================
# URTC Flasher - CAN bootloader OTA protocol implementation (URTCFlasher),
# matching bootloader_protocol.c's own state machine exactly. Transport-agnostic -
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
    HMAC_KEY, SLAVE_HMAC_KEY, STATUS_NAMES, THIS_HARDWARE_ID, VERIFY_FAIL_REASONS,
    CAN_ID_SLAVE_ENTER_BOOTLOADER, CAN_ID_SLAVE_START_UPDATE, CAN_ID_SLAVE_HMAC_CHUNK,
    CAN_ID_SLAVE_DATA, CAN_ID_SLAVE_END_UPDATE, CAN_ID_SLAVE_STATUS,
    CAN_ID_SLAVE_PROGRESS, CAN_ID_SLAVE_VERSION_RESP_1, CAN_ID_SLAVE_VERSION_RESP_2,
    CAN_ID_SLAVE_VERIFY_FAIL_REASON, CAN_ID_AUTHORIZE_DOWNGRADE,
    CAN_ID_READBACK, CAN_ID_READBACK_PAGE_ACK,
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
        # 0.8s, not the original 0.3s: on a busy/industrial bus, 0x7FA can
        # legitimately land noticeably later than 0x7F9 (both frames still
        # have to make it through arbitration against other real traffic),
        # and 0.3s left too little margin for that - confirmed real external
        # audit finding, 20 August 2026 external audit (see this project's
        # own auditoria_historial.txt for the finding number).
        GRACE_WINDOW = 0.8
        pending_bootloader_version = None  # in case 0x7FA arrives before 0x7F9
        while time.time() < deadline or (grace_deadline is not None and time.time() < grace_deadline):
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
                grace_deadline = time.time() + GRACE_WINDOW
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
        # Returns the manifest's own declared (major, minor) as a parsed
        # tuple if present and well-formed, else None - flash() uses this
        # in preference to its own hardcoded FIRMWARE_VERSION_MAJOR/MINOR
        # when available, same reasoning flash_slave() already documents
        # for why trusting a fixed constant regardless of which .bin was
        # actually selected would be wrong (that constant reflects this
        # tool's own currently-configured version, not necessarily the
        # specific file on disk - most likely to actually diverge exactly
        # when deliberately flashing an older file for a downgrade).
        manifest_path = firmware_path + ".manifest.json"
        if not os.path.isfile(manifest_path):
            return None
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.log(_("LOG_MANIFEST_UNREADABLE", e=e))
            return None

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

        parsed_version = None
        parts = str(version).split(".")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            parsed_version = (int(parts[0]), int(parts[1]))

        if not expected_sha256:
            self.log(_("LOG_MANIFEST_NO_SHA256_FIELD"))
            return parsed_version
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
        return parsed_version

    def flash(self, firmware_path, allow_downgrade=False):
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

        manifest_version = self._check_manifest(firmware_path, actual_sha256)
        report_major, report_minor = manifest_version if manifest_version else (FIRMWARE_VERSION_MAJOR, FIRMWARE_VERSION_MINOR)
        if manifest_version is None:
            # No manifest, or no parseable version field in it - falling
            # back to this tool's own configured version is only actually
            # correct when the selected file happens to match it. Usually
            # true (the common case is flashing the current build), but
            # worth a visible note specifically when downgrading, since
            # that's exactly the case where "assume it's the current
            # version" is most likely to be wrong.
            if allow_downgrade:
                self.log(_("LOG_NO_MANIFEST_VERSION_FOR_DOWNGRADE", major=report_major, minor=report_minor))

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
                # Small pacing gap - avoids overrunning the bootloader's own
                # receive/flash-write pace. On Windows specifically, this
                # relies on time.sleep() actually resolving to something
                # close to 1ms rather than the old ~15.6ms default system
                # timer tick that pre-3.11 CPython was subject to (which
                # would have made this whole page-transfer loop roughly an
                # order of magnitude slower than intended - a real,
                # previously-documented Windows Python gotcha, raised again
                # by the 20 August 2026 external audit). Measured directly
                # on this project's own target platform with the CPython
                # version this tool is actually built with: avg ~1.5ms,
                # nowhere near 15ms - CPython 3.11+ switched Windows
                # time.sleep() to a high-resolution waitable timer (see
                # CPython's own changelog, gh-93209) that no longer needs
                # the old timeBeginPeriod(1) workaround. requirements.txt
                # notes the recommended minimum Python version for this
                # reason - not enforced here, since a slower-than-ideal
                # transfer degrading gracefully is preferable to this tool
                # refusing to run at all on an older interpreter.
                time.sleep(0.001)
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

        # --- 0x7FD: authorize downgrade for THIS attempt, if requested -
        # must arrive before 0x7F4 below, since HandleEndUpdate consumes
        # the flag the moment its own anti-rollback check runs. Deliberate
        # magic payload (see CANBUS.TXT) - never sent unless the caller
        # explicitly opted in. ---
        if allow_downgrade:
            self.log(_("LOG_SENDING_AUTHORIZE_DOWNGRADE"))
            self.can.send_frame(CAN_ID_AUTHORIZE_DOWNGRADE, bytes([0xD0, 0x9E, 0x12, 0xAD]))
            time.sleep(0.01)

        # --- 0x7F4: end update (CRC32 + version) - report_major/minor
        # come from the firmware file's own manifest when available (see
        # _check_manifest above), not blindly from this tool's own
        # currently-configured FIRMWARE_VERSION_MAJOR/MINOR, since those 2
        # can genuinely differ - most likely exactly when allow_downgrade
        # is set. ---
        self.log(_("LOG_SENDING_END_UPDATE"))
        payload = struct.pack(">IHH", crc32, report_major, report_minor)
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

    def read_back_flash(self, output_path, timeout=180.0):
        """Reads the main board's own currently-installed firmware back
        over CAN (0x7FE/0x7FF - see CANBUS.TXT), unmodified, and writes it
        to output_path. The CAN equivalent of the SWD "back up entire
        flash before erasing" feature - worth doing before a normal
        update, and especially before an allow_downgrade one, since it's
        the only way to get the CURRENT bytes back later if the file
        that produced them isn't kept around. Bootloader-only (the board
        must already be sitting in the bootloader, same as flash() itself
        expects once triggered) - requires a bootloader that implements
        0x7FE; an older one simply never answers, surfaced here as a
        timeout rather than a silent empty file.
        """
        self.log(_("LOG_SENDING_READBACK_START"))
        self.can.send_frame(CAN_ID_READBACK, b"")

        # First reply is always DLC=4 (total size, 0 if nothing valid is
        # installed) - distinguished from the DLC=8 data replies that
        # follow purely by DLC, see CANBUS.TXT's own 0x7FE note.
        deadline = time.time() + 5.0
        total_size = None
        while time.time() < deadline:
            if self.stop_flag():
                raise FlashError("Cancelled by user")
            frame = self.can.read_frame(timeout=0.2)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_READBACK and len(data) == 4:
                total_size = struct.unpack(">I", data)[0]
                break
        if total_size is None:
            raise FlashError(_("LOG_READBACK_NO_RESPONSE"))
        if total_size == 0:
            raise FlashError(_("LOG_READBACK_NOTHING_INSTALLED"))
        self.log(_("LOG_READBACK_SIZE", size=total_size, kb=total_size / 1024))

        # The caller's own `timeout` (default 180s) was a flat constant
        # regardless of image size or bus speed - fine for a typical
        # update at 500 kbit/s, but a large image (up to APP_MAX_SIZE) at
        # one of this tool's own slower selectable SLCAN bitrates (as low
        # as 10 kbit/s - see SLCAN_BITRATES) can genuinely need longer than
        # that just for the raw transfer, before any retries - confirmed
        # real finding, 20 August 2026 external audit. Scaled by the now-
        # known total_size using a deliberately conservative floor
        # throughput (300 bytes/s - well under even 10 kbit/s's raw framed
        # ceiling, to also absorb per-page ACK round-trip overhead), with
        # a flat margin for connection/protocol overhead - never LOWER
        # than the caller's own request, only ever extended when the size
        # genuinely calls for it.
        MIN_READBACK_BPS = 300
        READBACK_MARGIN_S = 30.0
        effective_timeout = max(timeout, total_size / MIN_READBACK_BPS + READBACK_MARGIN_S)
        if effective_timeout > timeout:
            # Plain, untranslated diagnostic note (same pattern as
            # _check_manifest's own MANIFEST MISMATCH log above) rather
            # than a new language key - a one-line informational aside,
            # not user-facing UI text.
            self.log(
                f"Readback timeout extended to {int(effective_timeout)}s for this "
                f"{total_size}-byte image (the default {int(timeout)}s was sized "
                f"for a smaller image/faster bus than this one)."
            )

        buf = bytearray()
        page_index = 0
        transfer_start = time.time()
        while len(buf) < total_size:
            if time.time() - transfer_start > effective_timeout:
                raise FlashError(_("LOG_READBACK_TIMEOUT"))
            page_target = min(len(buf) + FLASH_PAGE_SIZE, total_size)
            page_deadline = time.time() + 5.0
            while len(buf) < page_target:
                if self.stop_flag():
                    raise FlashError("Cancelled by user")
                if time.time() > page_deadline:
                    raise FlashError(_("LOG_READBACK_PAGE_TIMEOUT", page=page_index))
                frame = self.can.read_frame(timeout=0.2)
                if frame is None:
                    continue
                can_id, data = frame
                if can_id == CAN_ID_READBACK and len(data) == 8:
                    buf.extend(data)
            # Acking unconditionally requests the next page even though buf
            # may have grown slightly past page_target (the board's own
            # final 8-byte frame in a page is only ever exactly sized to
            # what's left in that page, so this only happens if a stray
            # frame from elsewhere slipped through the same ID/DLC filter -
            # vanishingly unlikely, and self-corrects next page regardless).
            self.can.send_frame(CAN_ID_READBACK_PAGE_ACK, struct.pack(">I", page_index))
            page_index += 1
            pct = int((min(len(buf), total_size) / total_size) * 100)
            self.progress_cb(pct)

        with open(output_path, "wb") as f:
            f.write(bytes(buf[:total_size]))
        elapsed = time.time() - transfer_start
        kbps = (total_size / 1024) / elapsed if elapsed > 0 else 0.0
        self.log(_("LOG_READBACK_COMPLETE", size=total_size, path=output_path, elapsed=elapsed, kbps=kbps))
        return total_size

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
        # Slave board's own key, deliberately different from the master
        # board's HMAC_KEY used in flash_master above (see
        # slaveboot_common.h's own comment on why) - signing a slave
        # image with the master's key would make its bootloader reject
        # every real update sent to it.
        signature = hmac.new(SLAVE_HMAC_KEY, firmware, hashlib.sha256).digest()
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
        # Consecutive 0x216 polls that got no response at all - per
        # CANBUS.TXT's own 0x216 note, "no response" only ever means the
        # I2C transaction to the slave itself failed (bridge/slave gone),
        # never a legitimate "0% progress" answer (that case is 0xFF, a
        # real response). Without this counter, this loop would keep
        # blindly sending 0x213 frames into a stalled/disconnected bridge
        # all the way to the end of a large image (up to
        # SLAVE_APP_MAX_SIZE) before the failure ever surfaced, at
        # END_UPDATE - confirmed real finding, 20 August 2026 external
        # audit. 3 consecutive misses (roughly 6KB of blind sending, at
        # this loop's own ~2KB polling cadence) tolerates a single lost
        # 0x216 reply on a noisy bus without over-reacting, while still
        # aborting long before the remaining image would otherwise be
        # sent into nothing.
        consecutive_no_response = 0
        STALL_THRESHOLD = 3
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
                    consecutive_no_response = 0
                    self.log(_("LOG_SLAVE_PROGRESS", offset=offset, size=size, slave_pct=progress))
                else:
                    consecutive_no_response += 1
                    if consecutive_no_response >= STALL_THRESHOLD:
                        raise FlashError(
                            f"Expansion slave's I2C bridge stopped responding "
                            f"({consecutive_no_response} consecutive 0x216 progress "
                            f"queries with no answer) after sending {offset} of "
                            f"{size} bytes - aborting rather than continuing to "
                            f"send the rest of the image into a stalled/disconnected "
                            f"bridge. Check the slave chip is present and the I2C "
                            f"link is intact, then retry."
                        )

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
                reason_byte = self._query_slave_verify_fail_reason(timeout=1.0)
                if reason_byte is not None:
                    reason = VERIFY_FAIL_REASONS.get(reason_byte, f"unknown reason 0x{reason_byte:02X}")
                    raise FlashError(_("LOG_SLAVE_VERIFY_FAILED_REASON", reason=reason))
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

    def _query_slave_verify_fail_reason(self, timeout=1.0):
        # Same relay pattern as _query_slave_status/_query_slave_progress
        # above - only meaningful right after status reports
        # STATUS_VERIFY_FAIL (0x05), see CAN_ID_SLAVE_VERIFY_FAIL_REASON's
        # own comment in flasher_config.py.
        self.can.send_frame(CAN_ID_SLAVE_VERIFY_FAIL_REASON, b"")
        deadline = time.time() + timeout
        while time.time() < deadline:
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_SLAVE_VERIFY_FAIL_REASON and len(data) >= 1:
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
            # Same fail-fast reasoning as the main board's own _wait_for():
            # a genuine STATUS_VERIFY_FAIL here is a real, already-known
            # answer from the slave bootloader, not just "not yet the
            # status this call is waiting for" - sitting through the rest
            # of this timeout only to eventually raise a generic "Timed
            # out" message would hide that known cause and cost up to
            # `timeout` seconds for no reason.
            if status == 0x05:
                reason_byte = self._query_slave_verify_fail_reason(timeout=1.0)
                if reason_byte is not None:
                    reason = VERIFY_FAIL_REASONS.get(reason_byte, f"unknown reason 0x{reason_byte:02X}")
                    raise FlashError(_("LOG_SLAVE_VERIFY_FAILED_REASON", reason=reason))
                raise FlashError(_("LOG_SLAVE_VERIFY_FAILED"))
            time.sleep(0.2)
        raise FlashError(f"Timed out waiting for the expansion slave to report status 0x{expected_value:02X}")



