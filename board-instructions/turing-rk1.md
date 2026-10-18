## Before you start

- The RK1 is a compute module for the Turing Pi 2 board. Write the image to the module eMMC through the Turing Pi BMC.
- Update the BMC firmware to version 2.x first.

## Installation

1. Open the BMC web interface. Go to the **Flash Node** page.
2. Select the node and the Armbian image. Click **Install OS** and confirm.
3. Wait for the flash and the verification. Flashing takes about 8 minutes for each 1 GB of image.
4. The module reboots into Armbian after the verification.

The progress bar can show 100% too early. The flash continues in the background.

From the BMC command line, you can also run:

```sh
tpi flash --node 1 --image-path /path/to/Armbian.img
tpi power --node 1 on
```

## Serial console

- Use 115200 baud.
- The console is `ttyS9` on the `vendor` kernel and `ttyS0` on the `current` and `edge` kernels.

## Notes

- The RK3588 cannot boot directly from NVMe. Keep the bootloader on eMMC when you install the system to NVMe.

See the [Turing RK1 flashing guide](https://docs.turingpi.com/docs/turing-rk1-flashing-os).
