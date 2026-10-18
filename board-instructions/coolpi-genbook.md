## Before you start

The GenBook starts the mainline U-Boot from its SPI NOR flash. This U-Boot boots Armbian from a USB drive.

## Installation

1. Write the image to a USB drive.
2. Connect the USB drive to the GenBook.
3. Power on the GenBook.

## Rescue

Use this if the board does not boot after a write to SPI or eMMC.

1. Put the board in MaskROM mode. Hold the MaskROM button, or short the flash
   CLK pin to ground. Connect the OTG port to a Linux host and power on.
2. Erase the broken flash:
```sh
sudo rkdeveloptool ld
sudo rkdeveloptool db rk3588_spl_loader_v1.16.113.bin
sudo rkdeveloptool ef
```
3. Power off, release the button or remove the short, and boot from a microSD card.

The loader is in [armbian/rkbin](https://github.com/armbian/rkbin/tree/master/rk35).
See [Writing the image](https://docs.armbian.com/getting-started/writing-the-image/#rockchip).
