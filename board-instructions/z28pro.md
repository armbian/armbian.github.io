## Before you start

- The original Android firmware on the internal eMMC starts before the microSD card. Erase the eMMC before you boot Armbian from the microSD card.
- Use the Multitool from the [RK3318/RK3328 TV box forum thread](https://forum.armbian.com/topic/26978-csc-armbian-for-rk3318rk3328-tv-box-boards/) to back up and erase the eMMC.

## Installation

1. Write the Multitool to a microSD card. Boot the box from the card.
2. Optional: select **Backup flash** to save the original firmware.
3. Select **Erase flash**. Then shut down the box.
4. Write the Armbian image to a microSD card. Insert the card and power on the box.

## Rescue

Use this if the board does not boot after a write to SPI or eMMC.

1. Put the board in MaskROM mode. Hold the MaskROM button, or short the flash
   CLK pin to ground. Connect the OTG port to a Linux host and power on.
2. Erase the broken flash:
```sh
sudo rkdeveloptool ld
sudo rkdeveloptool db <loader for your SoC>
sudo rkdeveloptool ef
```
3. Power off, release the button or remove the short, and boot from a microSD card.

Loaders are in [armbian/rkbin](https://github.com/armbian/rkbin).
See [Writing the image](https://docs.armbian.com/getting-started/writing-the-image/#rockchip).
