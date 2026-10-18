## Before you start

The board boots from eMMC first. Press the BOOT button at power-on to boot from the microSD card.

## Installation

1. Hold the BOOT button.
2. Release the BOOT button after the power LED comes on.

## Notes

- Without the BOOT button, the board tries the microSD card only when eMMC boot fails.

## Rescue

Use this if the board does not boot after a write to eMMC.

1. Hold the BOOT button and connect power. The board boots the microSD card
   instead of the eMMC.
2. Rewrite the eMMC from the running system, or erase it. Identify the
   eMMC with `lsblk`; it is the `mmcblk*` device that is not the card you
   booted from:
```sh
sudo blkdiscard -f /dev/mmcblkX
```
3. Power off and remove the microSD card.
