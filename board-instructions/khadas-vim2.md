## Before you start

The board starts the OS on eMMC before the microSD card.

## Installation

1. Write the image to a microSD card.
2. Insert the card and power on the board.
3. Quickly press the FUNCTION key 3 times in 2 seconds. Release the key.
4. The board boots from the microSD card.

## Notes

Do not power the board from a PC USB port. The boot from microSD then fails.

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Hold the recovery button,
   or short the eMMC clock pin to ground. Check the vendor documentation for the
   button on your board.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
