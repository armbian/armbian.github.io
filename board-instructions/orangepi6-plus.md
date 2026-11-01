## Before you start

This is a generic UEFI image for Cix P1 (CD8180/CD8160) boards. It boots with ACPI. It does not use a device tree.

- The board firmware must support UEFI with ACPI (Arm SystemReady).

## Installation

1. Write the image to a USB drive.
2. Insert the USB drive and power on the board.
3. The UEFI firmware starts GRUB from the USB drive. GRUB starts Armbian.
