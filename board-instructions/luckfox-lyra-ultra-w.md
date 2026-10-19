## Before you start

- The board has eMMC and no microSD slot. Write the image to the eMMC over USB.
- Use `rkdeveloptool` (Linux) or RKDevTool (Windows).

## Installation

1. Hold the **BOOT** button and connect the USB-C OTG port to the computer.
2. On Linux, erase the eMMC and write the image at address 0:

```sh
sudo rkdeveloptool ld
sudo rkdeveloptool ef
sudo rkdeveloptool wl 0 Armbian_xxx_Luckfox-lyra-ultra-w_xxx.img
sudo rkdeveloptool rd
```

3. On Windows, select the image at address `0x0` in RKDevTool. Select the **Write by Address** check box, then start the write.

If the board is in MASKROM mode, load the [RK3506 loader](https://github.com/armbian/rkbin/blob/master/rk35/rk3506_loader_v1.09.112.bin) first with `sudo rkdeveloptool db rk3506_loader_v1.09.112.bin`.
