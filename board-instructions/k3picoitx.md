## Before you start

The board has no Armbian bootloader on the image. Write U-Boot to the on-board SPI flash once, with `fastboot`.

- Get the bootloader files from the `linux-u-boot-*-k3picoitx` package: `FSBL.bin`, `u-boot.itb`, `partition_4M.json`, `bootinfo_spinor.bin`, `u-boot-env-default.bin`, `esos.itb`, `fw_dynamic.itb`.
- Use a power supply that can feed the board, NVMe and USB devices. A 20 W PoE splitter causes silent resets.

## Installation

1. Power off the board. Hold the FDL button and connect power. Release the button.
2. Connect the second USB-C port to your computer.
3. Load and write the bootloader. Wait a few seconds between commands:

```sh
fastboot stage FSBL.bin && fastboot continue
sleep 10
fastboot oem speed:super-speed
fastboot stage u-boot.itb && fastboot continue
fastboot flash mtd partition_4M.json
fastboot flash bootinfo bootinfo_spinor.bin
fastboot flash fsbl FSBL.bin
fastboot flash env u-boot-env-default.bin
fastboot flash esos esos.itb
fastboot flash opensbi fw_dynamic.itb
fastboot flash uboot u-boot.itb
fastboot reboot
```

4. Write the Armbian image to a USB drive. Connect it to the board and power on.

## Install to internal storage

1. Boot Armbian from the USB drive.
2. Run `armbian-install`. Select the NVMe or UFS target.
3. Select **Boot from on-board SPI flash, full system on this disk**.
