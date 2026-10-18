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

## Rescue

Use this if the board does not boot after a write to SPI or eMMC.

1. Set SW1 to `00111` for SD/eMMC boot and boot a microSD card. Rewrite the SPI
   flash from the running system.
2. If the board does not reach a bootloader, set SW1 to `01001` for UART boot.
   Send the bootloader over the serial port with the Marvell
   [A3700-utils](https://github.com/MarvellEmbeddedProcessors/A3700-utils-marvell)
   UART download tool.
3. Set SW1 back to `00111` after the SPI flash is good again.
