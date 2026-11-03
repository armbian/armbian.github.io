## Boot from microSD card

1. Write the Armbian image to a microSD card.
2. Set both SW1 switches to ON (`11`). This selects microSD boot.
3. Insert the card and power the board.

## Install to eMMC

1. Boot Armbian from the microSD card.
2. Run `sudo armbian-install` and select the eMMC as the target.
3. Power off and remove the microSD card.
4. Set SW1 to `10` (eMMC boot).
5. Power on the board.

## Notes

- SW1 settings: `11` microSD boot, `10` eMMC boot, `01` USB download mode.
- Documentation: [DEBIX Model A on GitHub](https://github.com/debix-tech/debix-model-a).
