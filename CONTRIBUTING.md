# Contributing to URTC-FLASHER ⚡

## Technology Stack
- **Language**: Python.
- **Transports**: Serial (pyserial) and SocketCAN.

## Guidelines
1. **Verification**: Always implement read-back verification after a page write.
2. **Checksums**: Follow the big-endian CRC32/HMAC standard used by the URTC bootloader.
3. **UX**: Show clear error codes (e.g., `0x03` for HMAC failure) rather than generic error messages.
