## Before you start

- Write the image to the on-board eMMC over USB. Do not write it to a microSD card.
- Install the Rockchip `upgrade_tool` (Linux) or RKDevTool (Windows). See the [Luckfox flashing guide](https://wiki.luckfox.com/Luckfox-Nova/Flash-image).

## Installation

1. Hold the **BOOT** button and connect the USB-C port to the computer.
2. Release **BOOT** when the tool finds a LOADER device.
3. Write the image to eMMC at address 0 and reset the board:

```sh
sudo ./upgrade_tool wl 0 Armbian_xxx_Luckfox-rk3308b-nova_xxx.img
sudo ./upgrade_tool rd
```

On a running system, `sudo reboot loader` also starts the download mode.

## Serial console

- The debug console is UART4 (`ttyS4`) at 1500000 baud.
