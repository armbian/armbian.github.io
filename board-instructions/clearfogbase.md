## Before you start

Set the boot source with the SW1 DIP switch before you power on the board.

| Boot source | SW1 (switches 1-5, 1 = ON) |
|---|---|
| SD/eMMC | 00111 |
| SPI | 00010 |
| M.2 SSD | 11100 |
| UART | 01001 |

## Installation

- Set SW1 to `00111` (OFF, OFF, ON, ON, ON).

## Serial console

The UART adapter is on the board. Connect the micro-USB port. Use 115200 8N1.

## Notes

The microSD card is not accessible when the SOM has eMMC.
