## Before you start

- The image is not a microSD image. It has a rootfs image and an Android boot image for fastboot.
- The Armbian kernel boots from the `boot_b` partition.
- The kernel finds the root file system by UUID. Flash the rootfs image to a free partition.

## Installation

1. Put the device in fastboot mode.
2. Flash the rootfs image to a free partition. Flash the boot image to `boot_b`. Set slot B active:

```sh
fastboot flash <partition> Armbian_*.rootfs.img
fastboot flash boot_b Armbian_*.boot_sm8250-oneplus-kebab.img
fastboot set_active b
```

## Notes

- An Android update can change the active slot. If the Armbian kernel is in `boot_a`, set `abl_boot_partition_label=boot_a` in `/boot/armbianEnv.txt`.
- The [Xiaomi Elish flashing guide](https://github.com/amazingfate/armbian-xiaomi-elish/wiki/Flashing-Guide) shows the same flow, with a partition example.
