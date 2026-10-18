## Before you start

- The SoC boot ROM reads the eMMC before the microSD card.
- If the eMMC holds a bootable system, the board does not boot Armbian from the microSD card.

## Installation

1. Erase the eMMC if it holds Android or Linux. Follow the vendor guide: [Erase EMMC for SDcard Bootup](https://docs.banana-pi.org/en/BPI-CM4/GettingStarted_BPI-CM4#_erase_emmc_for_sdcard_bootup).
2. Write the image to a microSD card.
3. Insert the microSD card and power on the board.
