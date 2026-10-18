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

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Push the recovery button
   inside the AV jack with a toothpick, or short the eMMC clock pin to ground.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
