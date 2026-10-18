## Before you start

- The DIP switch SW7 selects the boot source. ON = High, OFF = Low.
- The image boots from the microSD slot SD1. Set SW7 for SD1 boot before power on.
- SW7.2 selects the boot I/O voltage: OFF = 3.3 V, ON = 1.8 V.

## Installation

1. Write the image to a microSD card and insert it into the SD1 slot.
2. Set SW7.1 ON to disable secure boot.
3. Set SW7.3 ON and SW7.4 OFF to select SD/eMMC boot.
4. Set SW7.7 ON to select SD1.
5. Connect a 5 V / 2 A adapter to the power jack CON2.
6. Press the RTC Wakeup button SW1 to turn on the power converters.

## Serial console

- Connect the USB VCOM port CON9 (micro-USB) to the PC. The console is `ttyS0` at 115200 baud.

## Notes

- Switch details: [NuMaker-IoT-MA35D1-A1 user manual](https://www.nuvoton.com/export/resource-files/en-us--UM_NuMaker_IoT_MA35D1_A1_EN_Rev1.12.pdf), section 3.11.
