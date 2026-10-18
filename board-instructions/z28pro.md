## Before you start

- The original Android firmware on the internal eMMC starts before the microSD card. Erase the eMMC before you boot Armbian from the microSD card.
- Use the Multitool from the [RK3318/RK3328 TV box forum thread](https://forum.armbian.com/topic/26978-csc-armbian-for-rk3318rk3328-tv-box-boards/) to back up and erase the eMMC.

## Installation

1. Write the Multitool to a microSD card. Boot the box from the card.
2. Optional: select **Backup flash** to save the original firmware.
3. Select **Erase flash**. Then shut down the box.
4. Write the Armbian image to a microSD card. Insert the card and power on the box.
