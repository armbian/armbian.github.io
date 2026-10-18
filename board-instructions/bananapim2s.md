## Before you start

- The SoC boot ROM reads the eMMC before the microSD card.
- If the eMMC holds a bootable system, the board does not boot Armbian from the microSD card.

## Installation

1. Erase the eMMC if it holds Android or Linux. Follow the vendor guide: [Erase EMMC for SDcard Bootup](https://wiki.banana-pi.org/Getting_Started_with_M2S#Erase_EMMC_for_SDcard_Bootup).
2. Write the image to a microSD card.
3. Insert the microSD card and power on the board.

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Hold the recovery button,
   or short the eMMC clock pin to ground. Check the vendor documentation for the
   button on your board.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
