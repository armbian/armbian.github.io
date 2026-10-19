## Before you start

- This image is for virtual machines, for example QEMU/KVM. Use `uefi-x86` for physical hardware.
- The image boots with UEFI or BIOS firmware. GRUB and the kernel show messages on the display and on the serial console `ttyS0`.

## Installation

1. Decompress the image.
2. Attach the image to the VM as a disk.
3. For a serial console only, start QEMU with `--display none --serial stdio`.
