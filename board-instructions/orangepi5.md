## Install to internal storage

The M.2 slot accepts an NVMe SSD or a SATA SSD. A SATA SSD needs the SATA bootloader in the SPI flash.

To install to an NVMe SSD:

1. Boot Armbian from the microSD card.
2. Run `armbian-install` and select the NVMe SSD.
3. Select **Boot from SPI/MTD flash, system on this disk**.

To install to a SATA SSD (`current` and `edge` kernels only):

1. Boot Armbian from the microSD card.
2. Add `sata0` to the `overlays=` line in `/boot/armbianEnv.txt`.
3. Reboot.
4. Run `armbian-install` and select the SATA SSD.
5. Select **Boot from SPI/MTD flash, system on this disk**.
6. Write the SATA bootloader to the SPI flash. `armbian-install` can write the NVMe bootloader instead.

```sh
sudo flashcp -v -p /usr/lib/linux-u-boot-*/u-boot-rockchip-spi-sata.bin /dev/mtd0
```

7. Power off the board. Remove the microSD card.

### Install the patched U-Boot for borked NVME on board revision v1.3.2

On board revisions matching exactly v1.3.2, NVME power support is broken on the regular U-Boot firmware. You must use a different U-Boot firmware on these boards to get NVME drives working.

1. Boot Armbian from the microSD card.

Write the firmware **ONLY** for v1.3.2 boards:
```sh
sudo flashcp -v -p /usr/lib/linux-u-boot-*/u-boot-rockchip-spi-v132.bin /dev/mtd0
```

## Rescue

Use this if the board does not boot after a write to SPI or eMMC.

1. Put the board in MaskROM mode. Hold the MaskROM button, or short the flash
   CLK pin to ground. Connect the OTG port to a Linux host and power on.
2. Erase the broken flash:
```sh
sudo rkdeveloptool ld
sudo rkdeveloptool db rk3588_spl_loader_v1.16.113.bin
sudo rkdeveloptool ef
```
3. Power off, release the button or remove the short, and boot from a microSD card.

The loader is in [armbian/rkbin](https://github.com/armbian/rkbin/tree/master/rk35).
See [Writing the image](https://docs.armbian.com/getting-started/writing-the-image/#rockchip).
