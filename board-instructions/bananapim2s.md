## Before you start

- The SoC boot ROM reads the eMMC before the microSD card.
- If the eMMC holds a bootable system, the board does not boot Armbian from the microSD card.

## Installation

1. Erase the eMMC if it holds Android or Linux. Follow the vendor guide: [Erase EMMC for SDcard Bootup](https://wiki.banana-pi.org/Getting_Started_with_M2S#Erase_EMMC_for_SDcard_Bootup).
2. Write the image to a microSD card.
3. Insert the microSD card and power on the board.
