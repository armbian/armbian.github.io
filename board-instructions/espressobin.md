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

## Rescue

Use this if the board does not boot after a `bubt` write to SPI flash.

1. Boot the board over the serial port. The Armada 3720 boot ROM waits for a
   UART download when the SPI flash holds no valid image.
2. Send a known good `flash-image-*.bin` with the Marvell
   [A3700-utils](https://github.com/MarvellEmbeddedProcessors/A3700-utils-marvell)
   UART download tool. The Armada 3720 does not use the Kirkwood `kwboot`
   protocol.
3. Write the image to SPI flash again with `bubt` from the U-Boot prompt.

The image must match the RAM size, chip count and speed of your board. A
mismatched image does not boot.
