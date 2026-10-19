## Before you start

- The board always boots from the microSD card if the card holds a valid image.
- Hold the MASKROM button during reset to stop boot from the internal SD NAND.

## Install to internal storage

Use these steps to write the image to the internal SD NAND (models with 2 GB or more).

1. Build [rkdeveloptool](https://github.com/rockchip-linux/rkdeveloptool) on a Linux PC.
2. Download the Radxa loader [rk3308_loader_uart0_m0_emmc_port_support_sd_20190717.bin](https://dl.radxa.com/rockpis/images/loader/rk3308_loader_uart0_m0_emmc_port_support_sd_20190717.bin).
3. Remove the microSD card. Connect the USB-C port to the PC.
4. Hold the MASKROM button and power on the board, or press RESET.
5. Release the MASKROM button after 2 seconds.
6. Write the decompressed image:

```sh
sudo rkdeveloptool db rk3308_loader_uart0_m0_emmc_port_support_sd_20190717.bin
sudo rkdeveloptool wl 0 Armbian.img
sudo rkdeveloptool rd
```

## Serial console

- Use UART0 at 1500000 baud, 8N1.
- Cable colors: black (left) = GND, white (center) = TX, green (right) = RX.

## Notes

- Boards with the RK3308B-S chip (marked RK3308BS) need the `bs` overlay. Add `overlays=bs` to `/boot/armbianEnv.txt`.
- Do not use the `bs` overlays on the RK3308B chip. This undervolts the CPU.
