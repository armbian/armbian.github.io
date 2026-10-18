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
