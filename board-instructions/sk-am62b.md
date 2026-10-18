## Before you start

The boot mode switches select the boot device. Set them to SD boot before you power on the board.

## Installation

1. Write the image to a microSD card and insert it.
2. Set the boot mode switches for SD boot:
   - SW2 (positions 1 to 8): `01000000`
   - SW1 (positions 1 to 8): `11000010`
   - `1` = ON, `0` = OFF.
3. Connect power.

## Notes

- Revision E1 boards use a different switch orientation. Follow the board silkscreen.
- Switch details: [SK-AM62 user guide](https://www.ti.com/lit/pdf/spruj40).
