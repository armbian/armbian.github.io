## Before you start

This is a generic UEFI image for Cix P1 (CD8180/CD8160) boards. It boots with ACPI. It does not use a device tree.

- The board firmware must support UEFI with ACPI (Arm SystemReady).
- Minisforum MS-R1: update the BIOS first. Without the update, boot stops at the initramfs. See the [MS-R1 SystemReady guide](https://github.com/minisforum-docs/MS-R1-Docs/blob/main/PlayBook/MS-R1-ARMSystemReady.md).

## Installation

1. Write the image to a USB drive.
2. Insert the USB drive and power on the board.
3. The UEFI firmware starts GRUB from the USB drive. GRUB starts Armbian.
