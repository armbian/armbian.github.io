## Before you start

- The original firmware on the internal flash starts before the microSD card. Erase the internal eMMC before you boot Armbian from the microSD card.
- Get the Multitool image from the [RK322x TV box forum thread](https://forum.armbian.com/topic/34923-csc-armbian-for-rk322x-tv-box-boards/).
- Test the Armbian image from the microSD card before you write it to the internal flash. A bad image can make the box unbootable.

## Installation

1. Write the Multitool to a microSD card. Boot the box from the card.
2. Optional: select **Backup flash** to save the original firmware.
3. Select **Erase flash**. Then shut down the box.
4. Write the Armbian image to a microSD card. Insert the card and power on the box.
5. After the first login, run `sudo rk322x-config`. Select the LED, WiFi chip and eMMC or NAND options of your box.

## Install to internal storage

1. Copy the Armbian image to the `images` folder on the NTFS partition of the Multitool card.
2. Boot the Multitool. Select **Burn image to flash** and select the eMMC device (usually `mmcblk2`).
3. Select **Shutdown**. Remove the power and the card, then connect the power again.

- For NAND boxes, use the Multitool option **Burn Armbian image via steP-nand** with the `legacy` kernel image. Do not erase the NAND.

## Serial console

- Use 115200 baud, not 1500000.
