## Before you start

- The image boots with the board's UEFI firmware. Update the UEFI firmware to the newest version first. See the [Debian HiKey960 page](https://wiki.debian.org/InstallingDebianOn/96Boards/HiKey960).
- To flash firmware, set the **Boot mode** and **Auto power** switches to ON. Set **Boot mode** to OFF for normal boot.

## Installation

- Press **ESC** at power on. Select the SD card boot entry.

## Serial console

- The UART is on the low-speed expansion header: pins 11 and 13, GND on pin 1 or 2.
- The UART uses 1.8 V logic. Do not use a 3.3 V or 5 V adapter.
- The console is `ttyAMA6` at 115200 baud.
