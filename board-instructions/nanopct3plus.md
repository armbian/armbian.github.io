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
