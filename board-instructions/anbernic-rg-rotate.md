## Before you start

The stock first-stage loader in the eMMC boot area does not start Armbian. Replace it one time.

- Download `<image>.spl.img` from the same release as the image. It is 4 MiB.
- Read `/boot/README.flash-bootloader-first.txt` on the written card. It has the full procedure and the recovery steps.
- Do not erase the stock Android partitions. The loader and the Wi-Fi, Bluetooth and audio firmware come from them.

## Installation

1. Boot a system with root access on the device: Armbian on another card, or Android with `adb root`.
2. Find the eMMC device. It is the `mmcblkN` with type `MMC` and `boot0`/`boot1` partitions.
3. Back up both boot areas to another computer.
4. Write the loader to `boot0` only:

```sh
echo 0 | sudo tee /sys/block/mmcblk3boot0/force_ro
sudo dd if=<image>.spl.img of=/dev/mmcblk3boot0 bs=1M conv=fsync
```

5. Power the device fully off, then on. A warm reboot is not a valid test.
6. If the device boots, write the same file to `boot1`.
7. Write the Armbian image to a microSD card and boot from it.

## Serial console

The board has no UART. The console is a USB gadget serial port (`ttyGS0`) on the USB-C port.

## Notes

- Audio starts after the second boot. The first boot extracts the firmware and rebuilds the initramfs.
- Android on the eMMC still boots when you remove the card.
