## Before you start

- The factory bootloader in the SPI flash cannot boot Armbian from the internal disk.
- To boot from internal storage, write the Armbian bootloader to the SPI flash.

## Install to internal storage

1. Boot Armbian from the microSD card.
2. Run `armbian-install`.
3. Select the internal disk as target.
4. Select **Boot from SPI/MTD flash, system on this disk**.
5. Power off the laptop and remove the microSD card.
