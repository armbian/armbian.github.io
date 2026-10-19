## Before you start

The board starts the bootloader on eMMC before the microSD card. The factory OS on eMMC blocks boot from microSD.

## Installation

Install Armbian to eMMC with Khadas OOWOW:

1. Write [vim3-oowow-latest-sd.img.gz](https://dl.khadas.com/products/oowow/system/vim3-oowow-latest-sd.img.gz) to a microSD card.
2. Copy the Armbian image file (`.img.xz`) to a USB drive. Do not write it with a flashing tool.
3. Insert the microSD card. Power on.
4. Hold FUNCTION and short press RESET. OOWOW starts.
5. Exit the wizard. Connect the USB drive.
6. Select **Write image to eMMC**. Select the Armbian image.

## Notes

To run Armbian from microSD, erase the eMMC bootloader first. See [Khadas: Erase eMMC](https://docs.khadas.com/products/sbc/vim3/development/erase-emmc).

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Hold the recovery button,
   or short the eMMC clock pin to ground. Check the vendor documentation for the
   button on your board.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
