## Before you start

- This image boots with its own mainline u-boot. The vendor u-boot on eMMC starts first and prevents this.
- Remove the vendor u-boot from the eMMC before you use this image.
- To keep Android and the vendor u-boot, use the `aml-s9xx-box` image instead.

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Push the recovery button
   inside the AV jack with a toothpick, or short the eMMC clock pin to ground.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
