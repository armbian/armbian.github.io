## Before you start

The device has no microSD slot. The SoC loads its bootloader only from the eMMC.

- Write a FIP with mainline U-Boot to the eMMC first. Get it from the [cainiao-cniot-core-linux releases](https://github.com/retro98boy/cainiao-cniot-core-linux/releases/tag/v2025.05.18).
- The USB-C port on the main unit is the USB download port.

## Installation

1. If Android or Linux runs with root access, write the FIP to the eMMC:

```sh
sudo dd if=fip-with-mainline-uboot.bin of=/dev/mmcblk1 bs=512 seek=1
echo 0 | sudo tee /sys/block/mmcblk1boot0/force_ro
echo 0 | sudo tee /sys/block/mmcblk1boot1/force_ro
sudo dd if=fip-with-mainline-uboot.bin of=/dev/mmcblk1boot0 bs=512 seek=1
sudo dd if=fip-with-mainline-uboot.bin of=/dev/mmcblk1boot1 bs=512 seek=1
```

2. Without root access, short the eMMC test point and power on. Write `fip-with-mainline-uboot.burn.img` with Amlogic USB Burning Tool.
3. Write the Armbian image to a USB drive. Insert it and power on.

If the device still boots from eMMC, delete the eMMC partition table. Mainline U-Boot then boots from USB.

## Install to internal storage

1. Boot Armbian from the USB drive.
2. Copy the image to the device over the network. Write it to `/dev/mmcblk1` with `dd`.
