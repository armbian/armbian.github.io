## Before you start

- The device has no microSD slot. Write the image to the 32 GB eMMC in Maskrom mode.
- You need a USB Type-A to Type-A cable and `rkdeveloptool` on a Linux PC.
- Download the RK3399 loader `rk3399_loader_v1.30.130.bin` from [retro98boy/tiannuo-tn3399-v3-linux](https://github.com/retro98boy/tiannuo-tn3399-v3-linux/tree/main/tools).

## Installation

1. Decompress the image to a `.img` file.
2. Set the DIP switch on the left side to **SERVICE** (right). Else the PC does not detect the Maskrom device.
3. Short the Maskrom pads and power on. See the pad photo in [retro98boy/smart-am40-linux](https://github.com/retro98boy/smart-am40-linux#maskrom短接点).
4. Connect the upper USB Type-A port on the front to the PC.
5. Write the image to the eMMC:

```sh
sudo rkdeveloptool db rk3399_loader_v1.30.130.bin
sudo rkdeveloptool wl 0 Armbian_*.img
sudo rkdeveloptool rd
```
