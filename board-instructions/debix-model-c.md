## Boot from microSD card

1. Write the Armbian image to a microSD card.
2. Set the DIP switch to `011`. This selects microSD boot.
3. Insert the card and power the board.

## Install to eMMC

1. Boot Armbian from the microSD card.
2. Run `sudo armbian-install` and select the eMMC as the target.
3. Power off and remove the microSD card.
4. Set the DIP switch to `010` (eMMC boot).
5. Power on the board.

## Boot from SPI NOR flash

1. Boot Armbian from the microSD card.
2. Run `sudo armbian-install` and select the SPI flash as the boot device. This replaces the vendor U-Boot in the SPI flash.
3. Set the DIP switch to `100` (SPI NOR boot).
4. U-Boot in the SPI flash boots Armbian from microSD first, then from eMMC.

## Notes

- DIP switch settings: `011` microSD boot, `010` eMMC boot, `100` SPI NOR boot, `001` USB download mode.
- Debug console: J1 pin 9 (RXD), pin 11 (TXD), pin 7 (GND), 3.3 V, 115200 baud.
- Wi-Fi is `wlan0`. Connect an antenna to the IPEX connector for usable range.
- Documentation: [DEBIX Model C on GitHub](https://github.com/debix-tech/debix-model-c).
