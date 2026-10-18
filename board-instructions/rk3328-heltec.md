## Before you start

- Write the image to the eMMC over USB with the Rockchip flash tools. See the [HT-M2808 forum thread](https://forum.armbian.com/topic/42946-csc-armbian-for-rk3328-heltec-ht-m2808-helium-miner/).
- Get the loader `rk3328_loader_ddr333_v1.16.250.bin`. The forum thread has the file.

## Installation

1. Power off the unit. Connect the USB cable to the back of the unit and to the computer.
2. Push and hold the reset button with a small pin. Connect the power cable.
3. Release the button when the tool finds the device.
4. Write the image at address 0 and reset the unit:

```sh
sudo rkdeveloptool ld
sudo rkdeveloptool wl 0 Armbian_xxx_Rk3328-heltec_xxx.img
sudo rkdeveloptool rd
```

If the unit is in MASKROM mode, load the loader first with `sudo rkdeveloptool db rk3328_loader_ddr333_v1.16.250.bin`.
