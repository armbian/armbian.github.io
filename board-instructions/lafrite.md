## Before you start

- La Frite has no microSD slot.
- The boot order is SPI flash bootloader, eMMC module, USB.
- Libre Computer eMMC modules ship with Android. The board always starts Android when this module is attached.

## Installation

1. Write the image to a USB drive.
2. Power off the board. Remove the eMMC module.
3. Connect the USB drive to the USB socket furthest from the GPIO header.

## Install to internal storage

Write the image to the eMMC module from a host PC:

1. Connect La Frite to the host PC with a USB A to USB A cable. Use the USB port closest to the IR sensor and the 40-pin header.
2. Connect a USB keyboard to the other USB port.
3. Power on. Press <kbd>Esc</kbd> during boot to open the boot menu.
4. Select **eMMC USB Drive Mode**. La Frite shows as a USB drive on the host PC.
5. Write the image to this drive.
6. Disconnect the USB A cable. Reboot La Frite.

## Notes

To update the SPI bootloader, write [aml-s805x-ac-spiflash.img](https://boot.libre.computer/release/aml-s805x-ac/aml-s805x-ac-spiflash.img) to a USB drive. Connect the drive and power on. Do not power off until the update is complete.

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Hold the recovery button,
   or short the eMMC clock pin to ground. Check the vendor documentation for the
   button on your board.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
