## Install to internal storage

The M.2 slot accepts an NVMe SSD or a SATA SSD. The SPI bootloader boots in this order: microSD, NVMe, SATA, eMMC.

To install to an NVMe SSD:

1. Boot Armbian from the microSD card.
2. Run `armbian-install` and select the NVMe SSD.
3. Select **Boot from SPI/MTD flash, system on this disk**.
4. Power off the board. Remove the microSD card.

To install to a SATA SSD, enable SATA on the M.2 slot first. This works on the `current` and `edge` kernels only.

1. Boot Armbian from the microSD card.
2. Add `sata2` to the `overlays=` line in `/boot/armbianEnv.txt`.
3. Reboot.
4. Run `armbian-install` and select the SATA SSD.
5. Select **Boot from SPI/MTD flash, system on this disk**.
6. Power off the board. Remove the microSD card.

## Notes

- If the board does not boot from eMMC, clear the SPI flash. Then try again. See the [Orange Pi 3B wiki](http://www.orangepi.org/orangepiwiki/index.php/Orange_Pi_3B) for the RKDevTool procedure.
