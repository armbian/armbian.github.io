## Before you start

The box starts the vendor u-boot on eMMC first. The image contains `u-boot.ext` and the multiboot scripts. The vendor u-boot uses them to start Armbian from the microSD card.

## Installation

1. Write the image to a microSD card.
2. Insert the card. Push the reset button inside the AV jack with a toothpick.
3. Hold the button and connect power. Release the button after some seconds.
4. If Android starts, repeat steps 2 and 3 with a longer or shorter hold time.

## Install to internal storage

- The image has no `armbian-install`.
- The install script keeps the vendor u-boot on eMMC.

1. Boot Armbian from the microSD card.
2. Run `/root/install-aml.sh`.
