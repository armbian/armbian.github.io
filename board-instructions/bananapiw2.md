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

## Rescue

Use this if the board does not boot after a write to eMMC.

1. Set switch SW4 to "1". The board boots the microSD card instead of the eMMC.
2. Rewrite the eMMC from the running system, or erase it. Identify the
   eMMC with `lsblk`; it is the `mmcblk*` device that is not the card you
   booted from:
```sh
sudo blkdiscard -f /dev/mmcblkX
```
3. Power off and remove the microSD card.

The SPI ROM code holds the first boot stage. A board that does not boot from a
microSD card with SW4 at "1" needs the SPI ROM update from the
[vendor page](https://docs.banana-pi.org/en/BPI-W2/BananaPi_BPI-W2).
