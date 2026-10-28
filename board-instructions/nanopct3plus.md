## Before you start

The board boots from the onboard eMMC before the microSD card. Use the BOOT key to boot from the microSD card.

## Installation

1. Insert the card into the board.
2. Hold the BOOT key beside the Ethernet port.
3. Connect the power supply.

## Install to internal storage

1. Boot Armbian from the microSD card.
2. Run `armbian-install` and select the eMMC.
3. Remove the microSD card. The board then boots from the eMMC without the BOOT key.

## Notes

- Armbian uses 4 of the 8 CPU cores. The bootloader leaves the second CPU cluster non-coherent.
- A warm `reboot` can hang. Disconnect and connect the power supply to restart the board.

## Rescue

Use this if the board does not boot after a write to eMMC.

1. Insert a microSD card with a working Armbian image.
2. Hold the BOOT key beside the Ethernet port and connect the power supply. The board boots the
   microSD card instead of the eMMC.
3. Rewrite the eMMC from the running system, or erase it. Identify the
   eMMC with `lsblk`; it is the `mmcblk*` device that is not the card you
   booted from:
```sh
sudo blkdiscard -f /dev/mmcblkX
```
4. Power off and remove the microSD card.
