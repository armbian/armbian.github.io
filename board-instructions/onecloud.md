## Before you start

- The board starts only the vendor u-boot on eMMC. The image does not contain a u-boot.
- You must start Armbian from the u-boot prompt. Connect a serial console (115200 baud).

## Installation

1. Write the image to a USB drive.
2. Connect the USB drive and the serial console. Power on the board.
3. Stop the autoboot at the u-boot prompt.
4. Run these commands:

```sh
setenv bootdev "usb 0"
usb start
fatload ${bootdev} 0x20800000 boot.scr && autoscr 0x20800000
```

## Notes

- To start Armbian from eMMC, run:

```sh
setenv bootdev "mmc 1"
fatload ${bootdev} 0x20800000 boot.scr && autoscr 0x20800000
```

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Push the recovery button
   inside the AV jack with a toothpick, or short the eMMC clock pin to ground.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
