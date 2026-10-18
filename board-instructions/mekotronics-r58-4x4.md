## Before you start

Write Armbian to the eMMC with `rkdeveloptool` in MaskROM mode. To enter MaskROM mode, erase the factory bootloader on the eMMC.

## Installation

1. Erase the bootloader. From a running Linux system, run (replace `X` with the eMMC device):

```sh
dd if=/dev/zero of=/dev/mmcblkX bs=1M count=8 conv=fsync
```

2. If you cannot run Linux, use the serial console. At the boot loader prompt, run:

```sh
mmc dev 0
mmc erase 0x0 0x2000
```

3. Connect the board to your computer with USB. Power on the board. The board starts in MaskROM mode.
4. Write the image with `rkdeveloptool`. Use the [RK3588 loader](https://dl.armbian.com/mekotronics-r58hd/u-boot/rk3588_spl_loader_v1.08.111.bin). See [Writing the image](https://docs.armbian.com/getting-started/writing-the-image/#rockchip).
