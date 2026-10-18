# Contributing to URTC-FLASHER ⚡

## Technology Stack
- **Language**: Python.
- **Transports**: Serial (pyserial) and SocketCAN.

## Guidelines
1. **Verification**: Never report a transfer as successful before the bootloader has confirmed every page (PAGE_ACK) and answered the end of the update with its verification status; the read-back of the copy is done by the bootloader, not by this tool.
2. **Checksums**: Follow the big-endian CRC32/HMAC standard used by the URTC bootloader.
3. **UX**: Show clear error codes (e.g., `0x03` for HMAC failure) rather than generic error messages.
