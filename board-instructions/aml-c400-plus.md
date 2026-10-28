## Before you start

The box starts the vendor u-boot on eMMC first. The image contains `u-boot.ext` and the multiboot scripts. The vendor u-boot uses them to start Armbian from the microSD card.

## Installation

1. Insert the card. Push the reset button inside the AV jack with a toothpick.
2. Hold the button and connect power. Release the button after some seconds.
3. If Android starts, repeat steps 2 and 3 with a longer or shorter hold time.

## Install to internal storage

- The image has no `armbian-install`.
- The install script keeps the vendor u-boot on eMMC.

1. Boot Armbian from the microSD card.
2. Run `/root/install-aml.sh`.

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Push the recovery button
   inside the AV jack with a toothpick, or short the eMMC clock pin to ground.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
