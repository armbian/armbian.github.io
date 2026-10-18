## Before you start

- Switch SW3 selects the boot device. The Armbian image boots from the microSD card only.
- SW3-A "1" and SW3-B "1": microSD card. SW3-A "0" and SW3-B "1": SPI-NAND. SW3-A "1" and SW3-B "0": eMMC.

## Installation

- Set SW3-A and SW3-B to "1".

## Notes

- The serial console shows "System halt!" when the selected boot device holds no system. Check SW3 and the microSD card.

## Rescue

Use this if the board does not boot after a write to SPI-NAND or eMMC.

1. Set SW3-A and SW3-B to "1". The board boots the microSD card, whatever the
   internal flash holds.
2. Rewrite the internal flash from the running system.
3. Set SW3 back to the device you want to boot.

"System halt!" on the serial console means the selected device holds no system.
Check SW3 first.
