## Before you start

The board ships with Petitboot in SPI flash. Petitboot starts first and cannot start Armbian.

## Installation

1. Write the image to a microSD card. Insert the card.
2. Turn the device upside down.
3. Press and hold the black button with a tool.
4. Keep the button pressed and connect power.
5. Release the button a few seconds after power on.
6. Log in on the console or over SSH.

Remove Petitboot. Then the board starts Armbian without the button. Use one of these methods:

- Write the Armbian bootloader to SPI flash: run `armbian-install`, then select **Flash / update the bootloader (u-boot) only** and **SPI / on-board flash (u-boot)**.
- Erase the SPI flash. The board then starts from the microSD card:

```sh
flash_erase /dev/mtd0 0 0
```

## Install to internal storage

The board has no eMMC. To run the system from a SATA disk, run `armbian-install`. Select the disk and **Boot from SPI/MTD flash, system on this disk**.
