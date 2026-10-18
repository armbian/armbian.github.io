## Before you start

The bootloader is in SPI flash. The factory bootloader must be replaced with the Armbian bootloader.

- Get the `flash-image-*.bin` files from the `linux-u-boot-*-espressobin` package.
- Select the file that matches your board: `flash-image-<DDR type>-<RAM size>_<chips>cs_<topology>-<CPU MHz>_<DDR MHz>.bin`.
- Read the RAM size and speeds from the current U-Boot boot messages.

## Installation

1. Copy the selected file to a FAT-formatted USB drive.
2. Insert the USB drive into the USB 3.0 port.
3. Stop the boot at the U-Boot prompt on the serial console.
4. Write the file to SPI flash:

```sh
bubt flash-image-<your-variant>.bin spi usb
```

5. Write the Armbian image to a microSD card. Insert it and reboot.

## Serial console

The Linux serial console is `ttyMV0`.
