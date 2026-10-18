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
