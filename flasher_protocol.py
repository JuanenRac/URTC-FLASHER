# =============================================================================
# URTC Flasher - CAN bootloader OTA protocol implementation (URTCFlasher),
# matching bootloader_protocol.c's own state machine exactly. Transport-agnostic -
# works with any object exposing send_frame/read_frame (SLCAN, SocketCAN,
# or MockCAN from flasher_transports.py).
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# (P1):
# every deadline/elapsed-time computation in this file uses time.monotonic()
# now, not time.time() - the civil (wall) clock can jump forward or backward
# at any moment (an NTP sync, a manual clock change) with no relation to how
# much real time has actually elapsed, which could silently shorten a real
# flashing timeout (aborting a write mid-page as "timed out" when the board
# was still working fine) or lengthen one (leaving a hung/unresponsive board
# waited on far longer than intended). time.monotonic() is never affected by
# either kind of adjustment - see Python's own docs. Nothing in this file
# ever uses one of these values as a real calendar date/timestamp (only for
# "how long has this taken" and "when should this deadline expire"), so
# there was no wall-clock use to preserve.
# =============================================================================
import hashlib
import hmac
import json
import os
import re
import struct
import time
import zlib

from flasher_config import (
    _, APP_MAX_SIZE, CAN_ID_BOOTLOADER_VERSION_RESPONSE, CAN_ID_DATA,
    CAN_ID_END_UPDATE, CAN_ID_ENTER_BOOTLOADER, CAN_ID_ERASE_FRAM,
    CAN_ID_FRAM_STATE_RESP, CAN_ID_HEARTBEAT, CAN_ID_HMAC_CHUNK, CAN_ID_PAGE_ACK,
    CAN_ID_QUERY_VERSION, CAN_ID_START_UPDATE, CAN_ID_STATUS, CAN_ID_VERSION_RESPONSE,
    ERASE_FRAM_MAGIC, FLASH_PAGE_SIZE, REQUIRE_PRODUCTION_SIGNATURE,
    HMAC_KEY, SLAVE_HMAC_KEY, STATUS_NAMES, THIS_HARDWARE_ID, VERIFY_FAIL_REASONS,
    CAN_ID_SLAVE_ENTER_BOOTLOADER, CAN_ID_SLAVE_START_UPDATE, CAN_ID_SLAVE_HMAC_CHUNK,
    CAN_ID_SLAVE_DATA, CAN_ID_SLAVE_END_UPDATE, CAN_ID_SLAVE_STATUS,
    CAN_ID_SLAVE_PROGRESS, CAN_ID_SLAVE_VERSION_RESP_1, CAN_ID_SLAVE_VERSION_RESP_2,
    CAN_ID_SLAVE_VERIFY_FAIL_REASON, CAN_ID_AUTHORIZE_DOWNGRADE,
    CAN_ID_READBACK, CAN_ID_READBACK_PAGE_ACK,
    SLAVE_HARDWARE_ID, SLAVE_APP_MAX_SIZE,
    CAN_ID_VERSION_PATCH_RESPONSE, PATCH_UNKNOWN, PATCH_FLAG,
)

class FlashError(Exception):
    pass


def minor_with_patch(info):
    """"minor" or "minor.patch" of a query_version() result, to show after the
    major in major.minor.patch; the patch only when the board sent it."""
    patch = info.get("version_patch")
    return str(info["version_minor"]) if patch is None else "{}.{}".format(info["version_minor"], patch)


class URTCFlasher:
    def __init__(self, slcan, log, progress_cb=None, stop_flag=None, speed_cb=None):
        self.can = slcan
        self.log = log
        self.progress_cb = progress_cb or (lambda pct: None)
        self.stop_flag = stop_flag or (lambda: False)
        # Separate, optional callback carrying the live transfer speed (in
        # kB/s) at the same cadence progress_cb already fires at. Kept
        # independent from progress_cb (rather than adding a second
        # positional/keyword argument to it) so every existing progress_cb
        # caller - including the ones already wired as single-argument
        # `lambda pct: ...` in the Qt Quick deck and the headless CLI -
        # keeps working unchanged; only callers that want the speed figure
        # need to pass this new callback.
        self.speed_cb = speed_cb or (lambda kbps: None)
        self._last_heartbeat_pct = None  # tracked across _wait_for calls for the page-ACK retry's active confirmation check

    def query_version(self, timeout=1.5, patch_grace=0.3):
        """Asks whatever's currently running (application or bootloader)
        to identify itself. Returns a dict with keys: responder ('application'
        or 'bootloader'), hardware_id, version_major, version_minor,
        version_patch (the installed application's patch number, or None when
        the board does not say), patch_aware (True when the board sent the
        optional 0x7E9 frame, False for a board that predates it),
        accepts_patch_in_end_update (True when the answering bootloader reads
        the patch from the minor field of the end-of-update frame) and
        bootloader_version (a (major, minor, patch) tuple, or None) - or
        None if nothing answered within the timeout (board unresponsive,
        wrong bitrate, not connected, etc.).

        bootloader_version only ever gets filled in when the BOOTLOADER is
        the one answering (responder == 'bootloader') - it comes from a
        separate 0x7FA frame the bootloader sends right alongside 0x7F9,
        which the running application never sends (it has no way to know
        a currently-flashed bootloader's version other than this). A short
        grace window after 0x7F9 arrives catches 0x7FA (and, for a board
        that has it, 0x7E9) even though the frames aren't guaranteed to land
        within the same read_frame() call. A board without 0x7E9 simply
        leaves the patch unknown after patch_grace seconds.
        """
        self.can.send_frame(CAN_ID_QUERY_VERSION, b"\x00")
        deadline = time.monotonic() + timeout
        result = None
        got_7f9_at = None
        # 0.8s, not the original 0.3s: on a busy/industrial bus, 0x7FA can
        # legitimately land noticeably later than 0x7F9 (both frames still
        # have to make it through arbitration against other real traffic),
        # and 0.3s left too little margin for that.
        GRACE_WINDOW = 0.8
        pending_bootloader_version = None  # in case 0x7FA arrives before 0x7F9
        pending_patch = None  # in case 0x7E9 arrives before 0x7F9: (patch byte, flags)
        while True:
            now = time.monotonic()
            if result is not None:
                have_boot = result["responder"] != "bootloader" or result["bootloader_version"] is not None
                if have_boot and result["patch_aware"]:
                    return result
                window = GRACE_WINDOW if not have_boot else patch_grace
                if now >= got_7f9_at + max(window, patch_grace):
                    return result
            elif now >= deadline:
                return None
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_VERSION_RESPONSE and len(data) == 8 and result is None:
                responder = "application" if data[0] == 0x00 else "bootloader"
                result = {
                    "responder": responder,
                    "hardware_id": struct.unpack(">I", data[1:5])[0],
                    "version_major": struct.unpack(">H", data[5:7])[0],
                    "version_minor": data[7],
                    "version_patch": None,
                    "patch_aware": False,
                    "accepts_patch_in_end_update": False,
                    "bootloader_version": pending_bootloader_version,
                }
                got_7f9_at = time.monotonic()
                if pending_patch is not None:
                    self._apply_patch_frame(result, pending_patch)
            elif can_id == CAN_ID_BOOTLOADER_VERSION_RESPONSE and len(data) == 3:
                if result is not None:
                    result["bootloader_version"] = (data[0], data[1], data[2])
                else:
                    # 0x7F9 hasn't arrived yet - hold onto this until it does,
                    # rather than discarding it just because of arrival order.
                    pending_bootloader_version = (data[0], data[1], data[2])
            elif can_id == CAN_ID_VERSION_PATCH_RESPONSE and len(data) >= 3:  # longer frames: extra bytes are ignored
                if result is not None:
                    self._apply_patch_frame(result, (data[1], data[2]))
                else:
                    pending_patch = (data[1], data[2])

    @staticmethod
    def _apply_patch_frame(result, patch_frame):
        patch_byte, flags = patch_frame
        result["patch_aware"] = True
        result["version_patch"] = None if patch_byte == PATCH_UNKNOWN else patch_byte
        result["accepts_patch_in_end_update"] = bool(flags & 1)

    @staticmethod
    def _end_update_minor_field(minor, patch, accepts_patch):
        """The 16-bit minor field of 0x7F4 / 0x214: the plain minor, or
        0x80 | PATCH in its high byte towards a bootloader that said it reads
        it. Anything else stays the legacy payload."""
        if accepts_patch and patch is not None and 0 <= patch <= 0x7F:
            return ((PATCH_FLAG | patch) << 8) | (minor & 0xFF)
        return minor

    def _wait_for(self, expected_id, timeout=2.0, expected_status_value=None):
        """Wait for a specific CAN ID, logging heartbeats/status seen along
        the way but not treating them as the answer unless they match.
        expected_status_value, when given (only meaningful alongside
        expected_id=CAN_ID_STATUS), additionally requires data[0] to equal
        that value before returning - otherwise a status frame carrying a
        different, intermediate value (e.g. STATUS_ERASING arriving before
        the STATUS_RECEIVING a caller actually needs) would be accepted as
        the answer just because the CAN ID matched."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.stop_flag():
                raise FlashError(_("ERR_CANCELLED_BY_USER"))
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
                    reason = VERIFY_FAIL_REASONS.get(data[1], _("ERR_UNKNOWN_REASON")) if len(data) == 2 else _("ERR_UNKNOWN_REASON")
                    raise FlashError(_("ERR_BOOTLOADER_VERIFY_FAILURE", reason=reason))
                if data[0] == 0xFF:
                    raise FlashError(_("ERR_BOOTLOADER_GENERIC_ERROR"))
                continue  # a status frame that didn't match - keep waiting, don't fall through to the generic check below
            if can_id == expected_id:
                return data
        raise FlashError(_("ERR_TIMEOUT_WAITING_CAN_ID", can_id=f"{expected_id:03X}"))

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

    def trigger_bootloader_entry(self, timeout=3.0):
        """Sends 0x7F0 to a currently-running application to make it reset
        into the bootloader. Skip this if the board is already sitting in
        the bootloader (fresh JTAG flash, or no valid application present)."""
        self.log(_("LOG_SENDING_BOOTLOADER_TRIGGER"))
        self.can.send_frame(CAN_ID_ENTER_BOOTLOADER, bytes([0xB0, 0x07, 0x1D, 0x5A]))
        # The bootloader listens for START_UPDATE (0x7F1) only during a window of about 600 ms after it starts, and then jumps back to the application; how soon it starts depends on
        # the size of the installed application (its CRC and HMAC are checked first). A fixed sleep either missed that window or was lucky, so the tool waits for the bootloader's own
        # first heartbeat (0x7F6, status "listening"), sent as soon as the window opens, and the caller then sends START_UPDATE at once. If no heartbeat is heard (an older
        # bootloader, a bus that drops frames) it falls back to the old behaviour: at least 0.8 s have gone by.
        started = time.monotonic()
        while time.monotonic() - started < max(timeout, 0.8):
            if self.stop_flag():
                raise FlashError(_("ERR_CANCELLED_BY_USER"))
            frame = self.can.read_frame(timeout=0.02)
            if frame is None:
                time.sleep(0.005)
                continue
            can_id, data = frame
            if can_id == CAN_ID_HEARTBEAT and len(data) >= 1 and data[0] == 0x01:
                self.log(_("LOG_BOOTLOADER_LISTENING"))
                return True
        remaining = 0.8 - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)
        return False

    def new_image_version(self, firmware_path, version=None):
        """The (major, minor) the image would install, from its manifest, the
        given version or its file name - or None. Never raises."""
        try:
            with open(firmware_path + ".manifest.json", "r", encoding="utf-8") as f:
                manifest = json.load(f)
            parts = str(manifest.get("version", "")).split(".") if isinstance(manifest, dict) else []
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return (int(parts[0]), int(parts[1]))
        except (OSError, ValueError):
            pass
        try:
            given = self._normalise_version(version)
        except FlashError:
            given = None
        return given or self._version_from_name(firmware_path)

    def new_image_patch(self, firmware_path, version=None):
        """The patch number (0-127) the image carries - the third part of the
        manifest's version, of the given version or of the file name
        (URTC_MAIN_FIRMWARE_v0.3.5.bin) - or None when it has none. Never raises."""
        candidates = []
        try:
            with open(firmware_path + ".manifest.json", "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if isinstance(manifest, dict):
                candidates.append(str(manifest.get("version", "")))
        except (OSError, ValueError):
            pass
        if isinstance(version, str):
            candidates.append(version.strip().lstrip("vV"))
        match = re.search(r"[vV](\d+\.\d+\.\d+)", os.path.basename(firmware_path))
        if match:
            candidates.append(match.group(1))
        for text in candidates:
            parts = text.split(".")
            if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                return int(parts[2]) if int(parts[2]) <= 0x7F else None
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return None  # a well-formed version without a patch: do not look further
        return None

    def report_version_change(self, firmware_path, target="master", version=None, timeout=1.5):
        """Before an update: asks the board what is installed, logs
        "installed X -> new Y" and warns when Y is older than X (the
        bootloader refuses that unless a downgrade is authorised, and a
        backup of the installed firmware is the safe thing to take first).
        Versions are shown as major.minor.patch when the side has a patch;
        the patch only takes part in the comparison when both sides carry
        one. Returns {"installed", "new", "downgrade", "installed_patch",
        "new_patch"}; a missing piece is None and nothing here ever stops the
        update."""
        installed = None
        installed_patch = None
        try:
            if target == "slave":
                info = self.query_slave_version(timeout=timeout)
                if info is not None and info["responder"] == "application":
                    installed = (info["app_version_major"], info["app_version_minor"])
                    installed_patch = info.get("app_version_patch")
            else:
                info = self.query_version(timeout=timeout)
                if info is not None and not (info["responder"] == "bootloader" and info["hardware_id"] == 0):
                    installed = (info["version_major"], info["version_minor"])
                    installed_patch = info.get("version_patch")
        except Exception:
            installed = None
            installed_patch = None
        new = self.new_image_version(firmware_path, version)
        new_patch = self.new_image_patch(firmware_path, version) if new is not None else None
        downgrade = installed is not None and new is not None and new < installed
        if (installed is not None and new is not None and new == installed
                and installed_patch is not None and new_patch is not None and new_patch < installed_patch):
            downgrade = True
        installed_text = self._version_text(installed, installed_patch)
        new_text = self._version_text(new, new_patch)
        if installed is None or new is None:
            self.log(_("LOG_VERSION_CHANGE_UNKNOWN", installed=installed_text or "?", new=new_text or "?"))
        else:
            self.log(_("LOG_VERSION_CHANGE", installed=installed_text, new=new_text))
        if downgrade:
            self.log(_("LOG_VERSION_DOWNGRADE_WARNING"))
        return {"installed": installed, "new": new, "downgrade": downgrade,
                "installed_patch": installed_patch, "new_patch": new_patch}

    @staticmethod
    def _version_text(version, patch=None):
        """"major.minor" or "major.minor.patch"; None when there is no version."""
        if version is None:
            return None
        return "{}.{}".format(*version) + ("" if patch is None else ".{}".format(patch))

    @staticmethod
    def _version_from_name(firmware_path):
        match = re.search(r"[vV](\d+)\.(\d+)(?:\.\d+)*", os.path.basename(firmware_path))
        return (int(match.group(1)), int(match.group(2))) if match else None

    def _resolve_version(self, firmware_path, manifest_info, version):
        for source in (manifest_info["version"], self._normalise_version(version), self._version_from_name(firmware_path)):
            if source is not None:
                return source
        raise FlashError(_("ERR_FIRMWARE_VERSION_UNKNOWN"))

    @staticmethod
    def _normalise_version(version):
        if version is None:
            return None
        if isinstance(version, str):
            parts = version.strip().lstrip("vV").split(".")
            version = (parts[0], parts[1]) if len(parts) >= 2 else (None, None)
        try:
            major, minor = int(version[0]), int(version[1])
        except (TypeError, ValueError, IndexError):
            raise FlashError(_("ERR_FIRMWARE_VERSION_UNKNOWN")) from None
        if not (0 <= major <= 255 and 0 <= minor <= 255):
            raise FlashError(_("ERR_FIRMWARE_VERSION_UNKNOWN"))
        return (major, minor)

    def _check_manifest_target(self, manifest, target):
        wanted_component, wanted_hardware = ("slave_application", SLAVE_HARDWARE_ID) if target == "slave" else ("main_application", THIS_HARDWARE_ID)
        component = manifest.get("component")
        if component in ("main_application", "slave_application") and component != wanted_component:
            raise FlashError(_("ERR_MANIFEST_WRONG_TARGET", got=component, want=wanted_component))
        declared = manifest.get("hardware_id")
        if declared not in (None, ""):
            try:
                declared_id = int(str(declared), 0)
            except ValueError:
                declared_id = None
            if declared_id is not None and declared_id != wanted_hardware:
                raise FlashError(_("ERR_MANIFEST_WRONG_TARGET", got=f"0x{declared_id:08X}", want=f"0x{wanted_hardware:08X}"))

    def _check_manifest(self, firmware_path, actual_sha256, target="master"):
        # Reads <firmware>.manifest.json, published by the URTC build next to
        # every image (see URTC docs/FIRMWARE_SIGNING.TXT). Returns a dict:
        #   "version": the declared (major, minor) - flash() reports it to the
        #              bootloader instead of this tool's own constant, which
        #              matters most for a deliberate downgrade;
        #   "hmac":    the published HMAC-SHA256 signature (32 bytes) or None.
        # A declared sha256 that does not match the file is a hard error: the
        # signature in that manifest belongs to some other file, so sending it
        # can only fail, and it usually means a wrong or corrupted download.
        info = {"version": None, "hmac": None}
        manifest_path = firmware_path + ".manifest.json"
        if not os.path.isfile(manifest_path):
            return info
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.log(_("LOG_MANIFEST_UNREADABLE", e=e))
            return info
        if not isinstance(manifest, dict):
            self.log(_("LOG_MANIFEST_UNREADABLE", e="not a JSON object"))
            return info

        # The manifest says which board the image is for. An image of the other board (the slave's, sent to the main board or the other way round) used to be transferred in full and
        # rejected only at the end by the HMAC check, with a misleading reason; it is refused here, before anything is sent.
        self._check_manifest_target(manifest, target)

        # str() before .lower(): a present-but-wrong-type value (null, a bare
        # number) must not raise AttributeError here.
        expected_sha256 = str(manifest.get("sha256", "") or "").lower().replace("0x", "")
        version = manifest.get("version", "?")
        build_date = manifest.get("build_date", "?")
        self.log(_("LOG_MANIFEST_INFO", version=version, build_date=build_date))

        parts = str(version).split(".")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            info["version"] = (int(parts[0]), int(parts[1]))

        if not expected_sha256:
            self.log(_("LOG_MANIFEST_NO_SHA256_FIELD"))
        elif expected_sha256 == actual_sha256.lower():
            self.log(_("LOG_MANIFEST_SHA256_MATCHES"))
        else:
            raise FlashError(_(
                "ERR_MANIFEST_MISMATCH", name=os.path.basename(manifest_path),
                expected=expected_sha256, actual=actual_sha256,
            ))

        if REQUIRE_PRODUCTION_SIGNATURE and str(manifest.get("signing_key_kind", "") or "").strip().lower() == "dev":
            raise FlashError(_("ERR_PRODUCTION_ONLY_DEV_KEY"))

        hmac_hex = str(manifest.get("hmac_sha256", "") or "").strip().lower().replace("0x", "")
        if hmac_hex:
            try:
                sig = bytes.fromhex(hmac_hex)
            except ValueError:
                sig = b""
            if len(sig) != 32:
                raise FlashError(_("ERR_HMAC_NOT_32_BYTES", name=os.path.basename(manifest_path)))
            info["hmac"] = sig
            kind = manifest.get("signing_key_kind", "?")
            self.log(_("LOG_USING_PUBLISHED_SIGNATURE", kind=kind))
            if kind == "dev":
                self.log(_("LOG_DEV_KEY_NOTE"))
        return info

    def _signature_for(self, firmware, manifest_info, key, board):
        """The published signature if there is one; otherwise a local HMAC
        with the key configured in urtc_config.json (bench boards with a
        self-built image); otherwise refuse - never sign with a made-up key."""
        if manifest_info["hmac"] is not None:
            return manifest_info["hmac"]
        if key:
            self.log(_("LOG_SIGNING_LOCALLY", board=board))
            return hmac.new(key, firmware, hashlib.sha256).digest()
        raise FlashError(_(
            "ERR_NO_SIGNATURE_NO_KEY", board=board,
            option="hmac_key_hex" if board == "master" else "slave_hmac_key_hex",
        ))

    def flash(self, firmware_path, allow_downgrade=False, version=None):
        self._last_heartbeat_pct = None  # a stale value from a prior flash()
        # call in this same session would otherwise always satisfy the
        # page-ACK retry's ">=" check below, regardless of this update's
        # actual progress.
        with open(firmware_path, "rb") as f:
            firmware = f.read()

        size = len(firmware)
        if size == 0:
            raise FlashError(_("ERR_FIRMWARE_EMPTY"))
        if size > APP_MAX_SIZE:
            raise FlashError(_("ERR_FIRMWARE_TOO_BIG_MAIN", size=size, max=APP_MAX_SIZE))

        crc32 = zlib.crc32(firmware) & 0xFFFFFFFF
        actual_sha256 = hashlib.sha256(firmware).hexdigest()
        manifest_info = self._check_manifest(firmware_path, actual_sha256)
        signature = self._signature_for(firmware, manifest_info, HMAC_KEY, "master")

        self.log(_("LOG_FIRMWARE_PATH", path=firmware_path))
        self.log(_("LOG_FIRMWARE_SIZE", size=size, kb=size/1024))
        self.log(_("LOG_FIRMWARE_CRC32", crc32=crc32))
        self.log(_("LOG_FIRMWARE_HMAC", hmac=signature.hex()))
        self.log(_("LOG_FIRMWARE_HARDWAREID", hw_id=THIS_HARDWARE_ID))

        # The version the bootloader records (and compares for the anti-rollback of the NEXT update) is the real version of this image: the manifest's, the one the caller gave, or the
        # one in the file name (URTC_MAIN_FIRMWARE_v0.3.3.bin). It is never invented: reporting a made-up 1.0 made every later official image look older and be rejected.
        report_major, report_minor = self._resolve_version(firmware_path, manifest_info, version)

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
        transfer_start = time.monotonic()
        total_retries = 0
        while offset < size:
            if self.stop_flag():
                raise FlashError(_("ERR_CANCELLED_BY_USER"))
            page_start = time.monotonic()
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
                # previously-documented Windows Python gotcha). Measured
                # directly on this project's own target platform with the
                # CPython version this tool is actually built with: avg ~1.5ms,
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
            # The bootloader writes (and acknowledges) a page when its 2048-byte buffer is FULL; the last page of an image that is not a whole
            # number of pages is written and acknowledged only when END_UPDATE (0x7F4) arrives. Waiting for that acknowledgement here would wait for a
            # message the bootloader sends only after one this tool sends only afterwards: so it is not waited for, and it is read after END_UPDATE.
            last_partial_page = page_end == size and (size % FLASH_PAGE_SIZE) != 0
            if last_partial_page:
                self.log(_("LOG_LAST_PARTIAL_PAGE_ACK_AFTER_END", page=page_index))
                acked_page = page_index
            else:
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
                    raise FlashError(_("ERR_PAGE_ACK_SHORT", page=page_index, got=len(ack)))
                # Only the first 4 bytes carry the page index - a longer ack
                # (DLC padding from the CAN controller, not necessarily an
                # error) shouldn't crash struct.unpack, which requires exactly
                # 4 bytes.
                acked_page = struct.unpack(">I", ack[:4])[0]
                if acked_page != page_index:
                    raise FlashError(_("ERR_PAGE_ACK_MISMATCH", expected=page_index, got=acked_page))
            page_elapsed = time.monotonic() - page_start
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
            self.speed_cb(page_kbps)
            self.log(_("LOG_PAGE_WRITTEN_ACKED", page=page_index, total=total_pages,
                      elapsed=page_elapsed, kbps=page_kbps))

        transfer_elapsed = time.monotonic() - transfer_start
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
        # The patch number rides in the high byte of the minor field, but only towards a bootloader that said (flag of 0x7E9, in its OWN answer) that it reads it; an image
        # without a patch, a board that does not answer or one that predates the extension gets the legacy payload.
        patch = self.new_image_patch(firmware_path, version)
        minor_field = report_minor
        if patch is not None:
            try:
                board = self.query_version(timeout=0.8)
            except Exception:
                board = None
            if board is not None and board["responder"] == "bootloader" and board["accepts_patch_in_end_update"]:
                minor_field = self._end_update_minor_field(report_minor, patch, True)
                self.log(_("LOG_END_UPDATE_WITH_PATCH", patch=patch))
        self.log(_("LOG_SENDING_END_UPDATE"))
        payload = struct.pack(">IHH", crc32, report_major, minor_field)
        self.can.send_frame(CAN_ID_END_UPDATE, payload)

        # The bootloader now verifies, then copies backup->main - this can
        # take several seconds for a large image (erase+write+read-back
        # verify per page). Watch for the final status.
        self.log(_("LOG_VERIFYING_COPYING_MAIN_SLOT"))
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            if self.stop_flag():
                raise FlashError(_("ERR_CANCELLED_BY_USER"))
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
                    reason = VERIFY_FAIL_REASONS.get(data[1], _("ERR_UNKNOWN_REASON_CODE", code=f"{data[1]:02X}"))
                    raise FlashError(_("ERR_BOOTLOADER_FAILURE_REASON", name=name, reason=reason))
                elif status in (0x05, 0xFF):
                    raise FlashError(_("ERR_BOOTLOADER_FAILURE", name=name))
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
        raise FlashError(_("ERR_TIMEOUT_FINAL_VERIFICATION"))

    def read_back_flash(self, output_path, timeout=180.0):
        """Reads the main board's own currently-installed firmware back
        over CAN (0x7FE/0x7FF - see CANBUS.TXT), unmodified, and writes it
        to output_path. The CAN equivalent of the SWD "back up entire
        flash before erasing" feature - worth doing before a normal
        update, and especially before an allow_downgrade one, since it's
        the only way to get the CURRENT bytes back later if the file
        that produced them isn't kept around. Bootloader-only (the board
        must already be sitting in the bootloader, same as flash() itself
        expects once triggered; with a valid application the bootloader
        leaves for it about 600 ms after reset unless an update starts) -
        requires a bootloader that implements 0x7FE; an older one simply
        never answers, surfaced here as a timeout rather than a silent
        empty file.
        """
        self.log(_("LOG_SENDING_READBACK_START"))
        self.can.send_frame(CAN_ID_READBACK, b"")

        # First reply is always DLC=4 (total size, 0 if nothing valid is
        # installed) - distinguished from the data replies that follow
        # purely by DLC, see CANBUS.TXT's own 0x7FE note. Data frames carry
        # 8 bytes, except the last one of the image when its size is not a
        # multiple of 8 (1 to 7 bytes).
        deadline = time.monotonic() + 5.0
        total_size = None
        while time.monotonic() < deadline:
            if self.stop_flag():
                raise FlashError(_("ERR_CANCELLED_BY_USER"))
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
        # that just for the raw transfer, before any retries. Scaled by
        # the now-known total_size using a deliberately conservative floor
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
        transfer_start = time.monotonic()
        while len(buf) < total_size:
            if time.monotonic() - transfer_start > effective_timeout:
                raise FlashError(_("LOG_READBACK_TIMEOUT"))
            page_target = min(len(buf) + FLASH_PAGE_SIZE, total_size)
            page_deadline = time.monotonic() + 5.0
            while len(buf) < page_target:
                if self.stop_flag():
                    raise FlashError(_("ERR_CANCELLED_BY_USER"))
                if time.monotonic() > page_deadline:
                    raise FlashError(_("LOG_READBACK_PAGE_TIMEOUT", page=page_index))
                frame = self.can.read_frame(timeout=0.2)
                if frame is None:
                    continue
                can_id, data = frame
                # The bootloader sends the LAST data frame of an image whose size is not a multiple of 8 with fewer bytes (DLC < 8): every frame of 1 to 8 bytes
                # is data here (the 4-byte size header was already read above), cut at the end of the page.
                if can_id == CAN_ID_READBACK and 1 <= len(data) <= 8:
                    buf.extend(data[: page_target - len(buf)])
            # The page is complete (the last frame of the image may be shorter than 8 bytes); the next one is requested.
            self.can.send_frame(CAN_ID_READBACK_PAGE_ACK, struct.pack(">I", page_index))
            page_index += 1
            pct = int((min(len(buf), total_size) / total_size) * 100)
            self.progress_cb(pct)
            running_elapsed = time.monotonic() - transfer_start
            running_kbps = (min(len(buf), total_size) / 1024) / running_elapsed if running_elapsed > 0 else 0.0
            self.speed_cb(running_kbps)

        with open(output_path, "wb") as f:
            f.write(bytes(buf[:total_size]))
        elapsed = time.monotonic() - transfer_start
        kbps = (total_size / 1024) / elapsed if elapsed > 0 else 0.0
        self.log(_("LOG_READBACK_COMPLETE", size=total_size, path=output_path, elapsed=elapsed, kbps=kbps))
        return total_size

    # -------------------------------------------------------------------
    # Expansion slave chip OTA - relayed through the main board's own
    # I2C bridge (CANBUS.TXT's own 0x210-0x219) rather than a direct CAN
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
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and (part1 is None or part2 is None):
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
        info = {
            "responder": "bootloader" if part1[0] == 0x01 else "application",
            "hardware_id": hw_id,
            "app_version_major": app_major,
            "app_version_minor": app_minor,
            "bootloader_version": part2[1],
            "app_version_patch": None,
            "bootloader_minor": None,
            "bootloader_patch": None,
            "accepts_patch_in_end_update": False,
        }
        if len(part2) >= 5:
            # The 5-byte form of 0x218 carries the patch numbers and also says that this slave bootloader reads the patch from the minor field of 0x214.
            info["app_version_patch"] = None if part2[2] == PATCH_UNKNOWN else part2[2]
            info["bootloader_minor"] = part2[3]
            info["bootloader_patch"] = part2[4]
            info["accepts_patch_in_end_update"] = True
        return info

    def flash_slave(self, firmware_path):
        """Same overall flow as flash() above, targeting the expansion
        slave chip instead - see this section's own header comment for
        the real protocol differences."""
        self._last_heartbeat_pct = None
        with open(firmware_path, "rb") as f:
            firmware = f.read()

        size = len(firmware)
        if size == 0:
            raise FlashError(_("ERR_FIRMWARE_EMPTY"))
        if size > SLAVE_APP_MAX_SIZE:
            raise FlashError(_("ERR_FIRMWARE_TOO_BIG_SLAVE", size=size, max=SLAVE_APP_MAX_SIZE))

        crc32 = zlib.crc32(firmware) & 0xFFFFFFFF
        actual_sha256 = hashlib.sha256(firmware).hexdigest()
        # Published by the URTC build with the slave board's own key
        # (different from the master's - see slaveboot_common.h).
        manifest_info = self._check_manifest(firmware_path, actual_sha256, target="slave")
        signature = self._signature_for(firmware, manifest_info, SLAVE_HMAC_KEY, "slave")

        self.log(_("LOG_FIRMWARE_PATH", path=firmware_path))
        self.log(_("LOG_FIRMWARE_SIZE", size=size, kb=size/1024))
        self.log(_("LOG_FIRMWARE_CRC32", crc32=crc32))
        self.log(_("LOG_FIRMWARE_HMAC", hmac=signature.hex()))
        self.log(_("LOG_SLAVE_FIRMWARE_HARDWAREID", hw_id=SLAVE_HARDWARE_ID))

        # The slave only takes START_UPDATE while its bootloader runs. An application that is still running ignores 0x211 (its register 0x01 is read-only), and the update then ends
        # in a generic timeout; saying it at once is more useful. (No answer at all is not taken as a refusal: the check is only for what is clearly the application.)
        state = self.query_slave_version()
        if state is not None and state.get("responder") == "application":
            raise FlashError(_("ERR_SLAVE_NOT_IN_BOOTLOADER"))

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
        transfer_start = time.monotonic()
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
        # END_UPDATE. 3 consecutive misses (roughly 6KB of blind sending, at
        # this loop's own ~2KB polling cadence) tolerates a single lost
        # 0x216 reply on a noisy bus without over-reacting, while still
        # aborting long before the remaining image would otherwise be
        # sent into nothing.
        consecutive_no_response = 0
        STALL_THRESHOLD = 3
        while offset < size:
            if self.stop_flag():
                raise FlashError(_("ERR_CANCELLED_BY_USER"))
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
                running_elapsed = time.monotonic() - transfer_start
                running_kbps = (offset / 1024) / running_elapsed if running_elapsed > 0 else 0.0
                self.speed_cb(running_kbps)
                if progress is not None:
                    consecutive_no_response = 0
                    self.log(_("LOG_SLAVE_PROGRESS", offset=offset, size=size, slave_pct=progress))
                else:
                    consecutive_no_response += 1
                    if consecutive_no_response >= STALL_THRESHOLD:
                        raise FlashError(_(
                            "ERR_SLAVE_BRIDGE_STALLED", count=consecutive_no_response, offset=offset, size=size,
                        ))

        transfer_elapsed = time.monotonic() - transfer_start
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
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                version_str = str(manifest.get("version", "0.0"))
                parts = version_str.split(".")
                slave_major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
                slave_minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        slave_minor_field = slave_minor
        slave_patch = self.new_image_patch(firmware_path)
        if slave_patch is not None and state is not None and state.get("accepts_patch_in_end_update"):
            slave_minor_field = self._end_update_minor_field(slave_minor, slave_patch, True)
            self.log(_("LOG_END_UPDATE_WITH_PATCH", patch=slave_patch))
        self.log(_("LOG_SENDING_END_UPDATE"))
        payload = struct.pack(">IHH", crc32, slave_major, slave_minor_field)
        self.can.send_frame(CAN_ID_SLAVE_END_UPDATE, payload)

        # --- Watch 0x216 (progress) and 0x215 (status) until the copy
        # finishes or fails - same 60s allowance as the main board's own
        # flow, for the same reason (erase+write+read-back verify per
        # page on a much slower bit-banged I2C write than the main
        # board's own direct flash access). ---
        self.log(_("LOG_VERIFYING_COPYING_MAIN_SLOT"))
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            if self.stop_flag():
                raise FlashError(_("ERR_CANCELLED_BY_USER"))
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
        raise FlashError(_("ERR_TIMEOUT_SLAVE_FINAL_VERIFICATION"))

    def _query_slave_status(self, timeout=1.0):
        self.can.send_frame(CAN_ID_SLAVE_STATUS, b"")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
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
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_SLAVE_VERIFY_FAIL_REASON and len(data) >= 1:
                return data[0]
        return None

    def _query_slave_progress(self, timeout=0.5):
        self.can.send_frame(CAN_ID_SLAVE_PROGRESS, b"")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = self.can.read_frame(timeout=0.1)
            if frame is None:
                continue
            can_id, data = frame
            if can_id == CAN_ID_SLAVE_PROGRESS and len(data) >= 1:
                return data[0]
        return None

    def _wait_for_slave_status(self, expected_value, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.stop_flag():
                raise FlashError(_("ERR_CANCELLED_BY_USER"))
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
        raise FlashError(_("ERR_TIMEOUT_SLAVE_STATUS", status=f"{expected_value:02X}"))



