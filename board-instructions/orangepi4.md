## Before you start

- The SoC boot ROM reads the eMMC before the microSD card.
- Boards with a factory bootloader on the eMMC start that bootloader, not the one on the Armbian microSD card.
- The factory bootloader is old. It can start Armbian from the microSD card, but it does not support all Armbian features.

## Installation

1. Write the image to a microSD card. Insert it and power on the board.
2. Log in. Find the eMMC: it is the `mmcblk` device with `boot0` and `boot1` partitions.
3. Back up the start of the eMMC, then erase the bootloader area. The eMMC partitions start at 16 MiB and stay intact:

```sh
sudo dd if=/dev/mmcblkX of=emmc-head-16M.bin bs=1M count=16
sudo dd if=/dev/zero of=/dev/mmcblkX bs=512 seek=64 count=32704 conv=fsync
```

4. Reboot. The board now starts the bootloader from the microSD card.

## Install to internal storage

1. Boot Armbian from the microSD card.
2. Run `armbian-install` and select the eMMC.
