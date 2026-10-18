## Before you start

The SoC boots in this order: SPI flash, eMMC, microSD. A system on the eMMC starts before the microSD card.

- To boot from microSD when the eMMC has a system, short jumper P10. P10 makes the SoC skip the eMMC.
- To skip SPI flash, short jumper P11.

## Installation

1. Write the image to a microSD card and insert it.
2. Connect the power connector before you connect the power adapter to mains.
3. If a UPS battery is installed, make sure the board is off. Hold the power button for about 4 seconds if the System ON LED is on.
4. Power on the board.

## Serial console

- Connect the USB-C port J15 to the computer. Jumper P13 must be open.
- Baud rate is 1500000.

## Rescue

Use this if the board does not boot after a write to SPI or eMMC.

1. Put the board in MaskROM mode. Hold the MaskROM button, or short the flash
   CLK pin to ground. Connect the OTG port to a Linux host and power on.
2. Erase the broken flash:
```sh
sudo rkdeveloptool ld
sudo rkdeveloptool db <loader for your SoC>
sudo rkdeveloptool ef
```
3. Power off, release the button or remove the short, and boot from a microSD card.

Loaders are in [armbian/rkbin](https://github.com/armbian/rkbin).
See [Writing the image](https://docs.armbian.com/getting-started/writing-the-image/#rockchip).
