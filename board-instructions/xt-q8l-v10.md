## Before you start

- The original firmware on the internal eMMC starts before the microSD card. Erase the eMMC before you boot Armbian from the microSD card.
- Get the Multitool image from the [RK3288 TV box forum thread](https://forum.armbian.com/topic/7141-armbian-for-rk3288-tv-box-boards-q8/).
- Test the Armbian image from the microSD card before you write it to the eMMC.

## Installation

1. Write the Multitool to a microSD card. Boot the box from the card.
2. Optional: select **Backup flash** to save the original firmware.
3. Select **Erase flash**. Then shut down the box.
4. Write the Armbian image to a microSD card or USB stick. Insert it.
5. Hold the power button for about 1 second to start the box.

## Notes

- After you install Armbian to eMMC, the U-Boot on eMMC always starts first. It then looks for a system on the microSD card, USB and eMMC, in this order.
- To make the box boot in MASKROM mode again, erase U-Boot from the eMMC. Check the device name first:

```sh
sudo dd if=/dev/zero of=/dev/mmcblk2 seek=64 count=8128 conv=sync,fsync
```
