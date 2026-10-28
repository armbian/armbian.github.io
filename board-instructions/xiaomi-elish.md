## Before you start

- The image is not a microSD image. It has a rootfs image and boot images for fastboot.
- The installation erases all Android data.
- Find the panel type. Run `cat /proc/cmdline` in an adb root shell or a recovery shell:
  - `qcom,mdss_dsi_k81_42_02_0a_dual_cphy_video` is a **CSOT** panel.
  - `qcom,mdss_dsi_k81_35_02_0b_dual_cphy_video` is a **BOE** panel.
- Make a free `linux` partition on the UFS. Shrink `userdata` from a recovery with `parted`. Follow the [flashing guide](https://github.com/amazingfate/armbian-xiaomi-elish/wiki/Flashing-Guide).

## Installation

1. Put the tablet in fastboot mode.
2. Erase `dtbo_b`, flash the rootfs image and the boot image for your panel, then set slot B active:

```sh
fastboot erase dtbo_b
fastboot flash linux Armbian_*.rootfs.img
fastboot flash boot_b Armbian_*.boot_sm8250-xiaomi-elish-boe.img   # or ...-csot.img
fastboot set_active b
```

3. Connect the USB-C port to a computer. Log in over the USB network with `ssh root@172.16.42.1`. The password is `1234`.

## Notes

- An Android update can change the active slot. If the Armbian kernel is in `boot_a`, set `abl_boot_partition_label=boot_a` in `/boot/armbianEnv.txt`.
