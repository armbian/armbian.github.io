## Before you start

The Armbian image has no bootloader. The board starts the image with the Libre Computer firmware in SPI flash.

## Notes

If the board does not start the image, update the SPI firmware:

1. Download [aml-s905d3-cc-spiflash.img](https://boot.libre.computer/release/aml-s905d3-cc/aml-s905d3-cc-spiflash.img).
2. Write the file to an empty USB drive.
3. Insert the USB drive into the board and power on. The board updates the SPI firmware.
4. Do not disconnect power until the update is complete.

For the USB ROM recovery method, see the [Libre Computer firmware guide](https://hub.libre.computer/t/how-to-flash-firmware-or-recover-firmware-on-libre-computer-aml-boards/4836).
