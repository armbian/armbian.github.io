## Before you start

- The board boots from the internal eMMC if the eMMC holds a valid image. Then it ignores the microSD card.
- Hold the MASKROM button during power on to disable the eMMC.
- The board has no RESET button. The white RECOVERY button has no function.

## Install to internal storage

1. Build [rkdeveloptool](https://github.com/rockchip-linux/rkdeveloptool) on a Linux PC.
2. Download the Radxa loader [rk3308_loader_uart0_m0_emmc_port_support_sd_20190717.bin](https://dl.radxa.com/rockpis/images/loader/rk3308_loader_uart0_m0_emmc_port_support_sd_20190717.bin).
3. Remove the microSD card. Connect the USB OTG port to the PC.
4. Hold the small black MASKROM button and power on the board.
5. Release the MASKROM button after 2 seconds.
6. Write the decompressed image:

```sh
sudo rkdeveloptool db rk3308_loader_uart0_m0_emmc_port_support_sd_20190717.bin
sudo rkdeveloptool wl 0 Armbian.img
sudo rkdeveloptool rd
```

## Serial console

- Use UART0 at 1500000 baud, 8N1.
- Cable colors: green (far left) = RX, white (center left) = TX, black (center right) = GND, red (far right) = +5V.
- Do not connect +5V if USB powers the board.

## Notes

- The internal WiFi chip antenna performs badly. Connect an external antenna and add `overlays=s0-ext-antenna` to `/boot/armbianEnv.txt`.
