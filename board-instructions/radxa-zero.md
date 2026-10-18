## Before you start

The board boots from eMMC before the microSD card. On models with eMMC, erase the eMMC before you boot Armbian from a microSD card.

## Installation

1. On a Linux PC, install `pyamlboot` and download the erase loader:

```sh
sudo pip3 install pyamlboot
curl -LO https://dl.radxa.com/zero/images/loader/radxa-zero-erase-emmc.bin
```

2. Hold the USB BOOT button on the board.
3. Connect the USB-C OTG port (marked USB-PWR) to the PC.
4. Release the USB BOOT button.
5. Erase the eMMC. If the eMMC is not fully clear, run the command a second time.

```sh
sudo boot-g12.py radxa-zero-erase-emmc.bin
```

6. Write the image to a microSD card and boot the board from it.

## Notes

- After step 5, the eMMC shows on the PC as a USB storage device. You can write the image directly to it.
- Radxa guide: [Install OS to eMMC](https://docs.radxa.com/en/zero/zero/low-level-dev/install-os-on-emmc).
