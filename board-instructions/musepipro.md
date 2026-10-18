## Before you start

- The factory bootloader in the SPI flash cannot boot Armbian from the eMMC or NVMe.
- To boot from internal storage, write the Armbian bootloader to the SPI flash.

## Install to internal storage

1. Boot Armbian from the microSD card.
2. Run `armbian-install`.
3. Select the eMMC or NVMe disk as target.
4. Select **Boot from SPI/MTD flash, system on this disk**.
5. Power off the board and remove the microSD card.

## Rescue

Use this if the board does not boot after a write to the SPI flash.

1. The K1 boot ROM waits for a USB download when the SPI flash holds no valid
   bootloader. Connect the USB port to a host.
2. Write the bootloader with `fastboot`. See the
   [U-Boot SpacemiT documentation](https://docs.u-boot.org/en/latest/board/spacemit/index.html).
3. Boot a microSD card and write the eMMC or NVMe again.
