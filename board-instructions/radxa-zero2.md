## Before you start

The board boots from eMMC before the microSD card. A bootloader on the eMMC prevents boot from the microSD card. Erase the eMMC first.

## Installation

1. On a Linux PC, install `pyamlboot` and download the Radxa erase loader:

```sh
sudo pip3 install pyamlboot
curl -LO https://dl.radxa.com/zero2pro/images/loader/radxa-zero-2pro-erase-emmc.bin
```

2. Hold the USB BOOT button on the board.
3. Connect the USB-C OTG port of the board to the PC.
4. Release the USB BOOT button.
5. Load the erase loader:

```sh
sudo boot-g12.py radxa-zero-2pro-erase-emmc.bin
```

6. The eMMC shows on the PC as a USB storage device. Write the Armbian image to this device.
7. Disconnect the board from the PC and power it on.

## Notes

- Radxa guide: [Install the system to eMMC](https://docs.radxa.com/en/zero/zero2pro/low-level-dev/install-os-on-emmc).

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Hold the recovery button,
   or short the eMMC clock pin to ground. Check the vendor documentation for the
   button on your board.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
