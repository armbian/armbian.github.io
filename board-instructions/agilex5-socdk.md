## Before you start

The microSD image has no SPL. The Secure Device Manager loads U-Boot SPL from QSPI flash. SPL then loads `u-boot.itb` from the microSD card.

- Program the QSPI flash with Quartus before the microSD card can boot.
- Merge `u-boot-spl-dtb.hex` from the `linux-u-boot-*-agilex5-socdk` package into your `.sof`/`.jic` file.

## Installation

1. Program the QSPI flash with the `.jic` file that contains the Armbian SPL.
2. Write the image to a microSD card.
3. Insert the card and power on the board.

## Serial console

`ttyS0` at 115200 baud.

## Notes

To configure the FPGA fabric at boot, copy your core image as `ghrd.core.rbf` to the FAT boot partition. U-Boot loads it and enables the bridges before Linux starts.
