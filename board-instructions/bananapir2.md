## Installation

1. Insert the microSD card and connect the power supply.
2. Hold the power button for about 10 seconds to power on the board.

## Install to internal storage

- The Armbian U-Boot does not boot from eMMC. Keep the system on the microSD card.

## Rescue

Use this if the board does not boot.

1. Write a working Armbian image to a microSD card.
2. Insert the card, connect the power supply and hold the power button for about
   10 seconds.

Armbian runs from the microSD card and does not write the eMMC, so a failed
update cannot leave the board without a boot device.
