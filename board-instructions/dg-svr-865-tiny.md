## Before you start

- The image is not a microSD image. It has a rootfs image and an Android boot image for fastboot.
- The Armbian kernel boots from the `boot_b` partition. The kernel finds the root file system by UUID.

## Installation

1. Put the board in fastboot mode.
2. Flash the rootfs image to a free partition. Flash the boot image to `boot_b`. Set slot B active:

```sh
fastboot flash <partition> Armbian_*.rootfs.img
fastboot flash boot_b Armbian_*.boot_qcs8250-dg-svr-865-tiny.img
fastboot set_active b
```

## Serial console

- The console is `ttyMSM0` at 115200 baud (8N1).
