## Before you start

- The boot ROM order is SPI flash, eMMC, microSD card.
- The factory bootloader on eMMC starts the microSD card first.
- Some units shipped since mid-2022 have a bootloader that can block boot from microSD.
- A switch under the bottom cover disables the eMMC. On some board revisions (v2.1), the switch label is wrong.

## Serial console

1. Remove the bottom cover.
2. Set the UART switch to ON (towards the display hinges). The headphone jack then carries the serial console, not audio.
3. Connect a 3.3 V serial adapter to the headphone jack. A 5 V adapter can damage the SoC.
4. Open the console at 1500000 baud:

```sh
picocom -b 1500000 /dev/ttyUSB0
```

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
