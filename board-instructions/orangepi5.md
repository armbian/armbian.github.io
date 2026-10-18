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
