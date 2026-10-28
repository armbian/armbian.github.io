## Before you start

The board ships with Petitboot in SPI flash. Petitboot starts before the microSD card.

## Installation

1. Write the image to a microSD card. Insert the card.
2. Hold the recovery (RCY) button and power on the board.
3. Release the RCY button after the blue LED flashes once.

## Install to internal storage

1. Run `armbian-install`.
2. Select **Flash / update the bootloader (u-boot) only**, then **SPI / on-board flash (u-boot)**. This step removes Petitboot permanently.
3. Optional: run `armbian-install` again to install the system to eMMC, NVMe or USB.

If you keep Petitboot, you must hold the RCY button at every boot.
