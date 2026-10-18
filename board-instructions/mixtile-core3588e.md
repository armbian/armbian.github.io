## Before you start

- The microSD slot on the carrier board does not work. Write Armbian to the eMMC on the module.
- The micro-USB port is the OTG port. Use it to write the image from your computer.

## Installation

1. Connect the **FCREC** and **GND** pins with a jumper cap. This enters recovery mode. It works only if the bootloader on the eMMC works.
2. Connect the micro-USB port to your computer and power on the board.
3. Write the image with `rkdeveloptool`. See [Writing the image](https://docs.armbian.com/getting-started/writing-the-image/#rockchip).
4. Remove the jumper cap and reboot.

## Notes

- If the bootloader is broken, enter real MaskROM mode. Short the two solder joints near the SoC on the module. See the [Mixtile picture](https://dh19rycdk230a.cloudfront.net/app/uploads/2023/11/solder-joints.png).
- U-Boot boot order: NVMe, USB, eMMC.
