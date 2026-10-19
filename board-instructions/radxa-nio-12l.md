## Before you start

- The board loads its bootloader from UFS only. The Armbian image does not contain a bootloader.
- Use the image marked **UFS**. UFS images use 4096-byte sectors.
- From the download page, also get the **FIP** (`.fip.img`) and **LK** (`.lk.bin`) files of the same build.
- Build [mtk-flash](https://github.com/grinn-global/mtk-flash) on a Linux PC. Add your user to the `dialout` group.

## Installation

1. Decompress the image to a `.img` file.
2. Start the flash on the PC:

```sh
mtk-flash --da Armbian.lk.bin --fip Armbian.fip.img --img Armbian.img --dev /dev/ttyACM0
```

3. Hold the Download button on the board.
4. Connect the USB-C OTG port of the board to the PC.
5. Release the Download button. The green LED flashes while the flash runs.
6. When the flash completes, disconnect the USB cable and power on the board.

## Serial console

- Use UART0 (`ttyS0`) at 921600 baud.

## Notes

- If the PC shows `/dev/ttyACM0` before step 3, another device uses that name. Set `--dev` to the new `ttyACM` device.
