## Before you start

The factory system on the SPI NAND flash starts before the microSD card. Erase the SPI NAND flash before you boot Armbian from the microSD card.

## Installation

1. Hold the **BOOT** button and connect the board to the computer over USB.
2. Erase the onboard flash. On Windows, use **Erase All** in RKDevTool. On Linux, run:

```sh
sudo rkdeveloptool ld
sudo rkdeveloptool ef
```


If the board is in MASKROM mode, load the [RK3506 loader](https://github.com/armbian/rkbin/blob/master/rk35/rk3506_loader_v1.09.112.bin) first with `sudo rkdeveloptool db rk3506_loader_v1.09.112.bin`.