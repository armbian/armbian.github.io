## Before you start

- Armbian runs from the onboard eMMC. Write the image to the eMMC over USB in firmware update (Maskrom) mode.
- You need a USB Type-A to Type-A cable and `rkdeveloptool` on a Linux PC.
- Download the loader [RK3576_MiniLoaderAll.bin](https://dl.photonicat.com/images/photonicat2/RK3576_MiniLoaderAll.bin).

## Installation

1. Decompress the image to a `.img` file.
2. Turn off the device.
3. Press the power button 3 times, then hold it for more than 10 seconds.
4. Make sure that the power LED flashes fast (0.25 s on, 0.25 s off).
5. Connect the USB OTG port to the PC with the Type-A to Type-A cable.
6. Write the image to the eMMC:

```sh
sudo rkdeveloptool db RK3576_MiniLoaderAll.bin
sudo rkdeveloptool wl 0 Armbian_*.img
sudo rkdeveloptool rd
```

## Notes

- Vendor guide: [Flash system images to the onboard eMMC](https://photonicat.com/wiki/Build_system_image_for_photonicat2#Flash_system_images_to_the_onboard_eMMC).
