## Before you start

- The board has no microSD slot. It boots from the onboard eMMC only.
- Write the image with the NXP `uuu` tool over USB. Get it from [NXP mfgtools](https://github.com/nxp-imx/mfgtools/releases).
- You need the bootloader file `flash.bin` together with the image. The `linux-u-boot-vendor-maaxboard-8ulp` package contains it in `/usr/lib/linux-u-boot-vendor-maaxboard-8ulp/`.
- Boot switch SW1 positions 1 to 6:
  - Serial Download Mode: only SW1-4 ON.
  - Internal Boot Mode (eMMC): only SW1-5 ON.

## Installation

1. Decompress the image.
2. Set SW1 to Serial Download Mode.
3. Connect J7 (USB-C power) and J4 (USB debug / download) to the host PC.
4. Power on the board. Run `lsusb` and make sure that the NXP device shows.
5. Write the bootloader and the image to the eMMC:

```sh
sudo uuu -v -b emmc_all flash.bin Armbian_*.img
```

6. Set SW1 to Internal Boot Mode.
7. Power cycle the board.

## Serial console

- Connect to J4. The console is `ttyLP1` at 115200 baud.
