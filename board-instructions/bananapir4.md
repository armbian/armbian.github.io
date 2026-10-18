## Before you start

- Switch SW3 selects the boot device. The Armbian image boots from the microSD card only.
- SW3-A "1" and SW3-B "1": microSD card. SW3-A "0" and SW3-B "1": SPI-NAND. SW3-A "1" and SW3-B "0": eMMC.

## Installation

- Set SW3-A and SW3-B to "1".

## Notes

- The serial console shows "System halt!" when the selected boot device holds no system. Check SW3 and the microSD card.
