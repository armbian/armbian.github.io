## Before you start

- Set switch SW4 to "1" to boot from the microSD card.
- Boards with old SPI ROM code do not boot from the microSD card. Update the SPI ROM first. See the FAQ on the [vendor page](https://docs.banana-pi.org/en/BPI-W2/BananaPi_BPI-W2).

## Install to internal storage

1. Boot Armbian from the microSD card.
2. Run `armbian-install` and select the eMMC.
3. Remove the microSD card and reboot.

## Notes

- Armbian on eMMC uses only 1 GiB of the 2 GiB RAM. The eMMC boot data starts only one of the two DRAM controllers.
- To use 2 GiB RAM, run Armbian from the microSD card.
