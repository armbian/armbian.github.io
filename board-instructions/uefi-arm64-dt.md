## Before you start

This is a generic image for arm64 computers with UEFI firmware that boot with a device tree, for example Snapdragon X laptops. The kernel selects the device tree for the computer at boot.

- Disable Secure Boot in the firmware settings. The Armbian boot loader and kernel are not signed.

## Installation

1. Write the image to a USB drive.
2. Insert the USB drive and power on the computer.
3. Open the firmware boot menu. Select the USB drive.
4. GRUB starts Armbian.
