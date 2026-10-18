## Before you start

- The original firmware on the internal eMMC starts before the microSD card. Erase the eMMC before you boot Armbian from the microSD card.
- Get the Multitool image from the [RK3318/RK3328 TV box forum thread](https://forum.armbian.com/topic/26978-csc-armbian-for-rk3318rk3328-tv-box-boards/).
- Test the Armbian image from the microSD card before you write it to the eMMC. A bad image can make the box unbootable.
- On some boxes the microSD slot cannot boot. On these boxes, write Armbian directly to the eMMC with the Multitool.

## Installation

1. Write the Multitool to a microSD card. Boot the box from the card.
2. Optional: select **Backup flash** to save the original firmware.
3. Select **Erase flash**. Then shut down the box.
4. Write the Armbian image to a microSD card. Insert the card and power on the box.
5. After the first login, run `sudo rk3318-config` to set the options for your box.

## Install to internal storage

1. Copy the Armbian image to the `images` folder on the NTFS partition of the Multitool card.
2. Boot the Multitool. Select **Burn image to flash** and select the eMMC device (usually `mmcblk2`).
3. Select **Shutdown**. Remove the power and the card, then connect the power again.

## Serial console

- Use 1500000 baud.
