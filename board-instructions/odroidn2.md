## Before you start

- The board has a boot select switch with two positions: SPI and MMC.
- SPI: the board starts Petitboot from SPI flash.
- MMC: the board starts the bootloader on eMMC. If the eMMC has no bootloader, the board starts the microSD card.
- Do not move the switch or change the eMMC module while the board has power.

## Installation

1. Write the image to a microSD card.
2. Power off the board. Set the boot switch to MMC.
3. Insert the card and power on the board.

## Install to internal storage

To boot from a USB drive, put the Armbian bootloader in SPI flash:

1. Boot Armbian from the microSD card or eMMC.
2. Run `armbian-install`.
3. Select **Flash / update the bootloader (u-boot) only**, then **SPI / on-board flash (u-boot)**.
4. Run `armbian-install` again. Select the USB drive and **Boot from SPI/MTD flash, system on this disk**.
5. Power off the board. Set the boot switch to SPI.

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Hold the recovery button,
   or short the eMMC clock pin to ground. Check the vendor documentation for the
   button on your board.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
