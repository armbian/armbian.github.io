## Before you start

This image is for the NanoPi M3 and the NanoPC-T3.
The NanoPC-T3 boots from the onboard eMMC before the microSD card. Use the BOOT key to boot from the microSD card.

## Installation

1. Insert the card into the board.
2. On the NanoPC-T3, hold the BOOT key.
3. Connect the power supply.

## Notes

- Armbian uses 4 of the 8 CPU cores. The bootloader leaves the second CPU cluster non-coherent.
- A warm `reboot` can hang. Disconnect and connect the power supply to restart the board.
