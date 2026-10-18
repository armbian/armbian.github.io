## Before you start

- The board has no microSD slot. The boot ROM loads the bootloader from eMMC.
- The disk image cannot carry the bootloader. Write it to eMMC by hand, once.
- Two bootloader files come with the image: `*.bl2.img` and `*.fip.bin`.
- Keep a serial adapter (115200 baud) ready. A bad bootloader leaves the board without a prompt.

## Installation

1. Write the image to a USB stick.
2. Boot the board into the factory OpenWrt and copy both bootloader files to the board.
3. Replace the factory bootloader:
```sh
echo 0 > /sys/block/mmcblk0boot0/force_ro
dd if=Armbian-*.bl2.img of=/dev/mmcblk0boot0 bs=1M conv=fsync
echo 1 > /sys/block/mmcblk0boot0/force_ro
dd if=Armbian-*.fip.bin of=/dev/mmcblk0p4 bs=1M conv=fsync
sync
```
4. Connect the USB stick and reboot. U-Boot boots from USB before eMMC.

## Install to internal storage

1. Run `armbian-install` and select the eMMC.
2. Remove the USB stick and reboot.
3. For NVMe, select the NVMe drive and the standalone option. U-Boot boots NVMe before eMMC.

## Notes

- The boot ROM does not boot from SPI-NAND. To recover, use UART download mode and the `mtk_uartboot` tool.
