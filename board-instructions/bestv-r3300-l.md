## Before you start

The stock bootloader on the eMMC starts before the microSD card. Disable the eMMC for the first boot, then erase its bootloader.

## Installation

1. Write the image to a microSD card and insert it.
2. Connect the eMMC CLK test point to GND.
3. Power on the box. Remove the short after 1 second. If you wait longer, Linux cannot use the eMMC.
4. The box boots Armbian from the microSD card.
5. Erase the eMMC bootloader so that later boots do not need the short:

```sh
echo 0 | sudo tee /sys/block/mmcblk1boot0/force_ro
echo 0 | sudo tee /sys/block/mmcblk1boot1/force_ro
sudo dd if=/dev/zero of=/dev/mmcblk1boot0 bs=1MiB count=4
sudo dd if=/dev/zero of=/dev/mmcblk1boot1 bs=1MiB count=4
sudo dd if=/dev/zero of=/dev/mmcblk1 bs=1MiB count=4
```

## Install to internal storage

1. Boot Armbian from the microSD card.
2. Write the Armbian image directly to `/dev/mmcblk1` with `dd`.
