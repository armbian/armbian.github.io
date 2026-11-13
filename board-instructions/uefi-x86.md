## Before you start

This is a generic image for x86_64 computers with UEFI or BIOS firmware. There is no SD card image.

- Disable Secure Boot in the firmware settings. The Armbian boot loader and kernel are not signed.

## Installation

1. Write the image to a USB drive.
2. Insert the USB drive and power on the computer.
3. Open the firmware boot menu. Select the USB drive.
4. GRUB starts Armbian.

## NVIDIA graphics

The desktop images include the latest NVIDIA driver. On a computer without an NVIDIA GPU, Armbian removes it.

The latest driver supports Turing (GeForce RTX 20 and GTX 16) and newer GPUs. Armbian does not support older GPUs. To use an older GPU, install the legacy driver yourself.

Ubuntu:

```sh
sudo apt purge '~nnvidia' '~nlibnvidia'
sudo apt autoremove --purge
sudo apt install nvidia-driver-580
```

Debian: the legacy driver has the same package names. Pin it, else an upgrade installs the latest driver again.

```sh
sudo tee /etc/apt/preferences.d/nvidia-legacy << 'EOF'
Package: nvidia-* libnvidia-* libcuda* libnvcuvid* firmware-nvidia-* xserver-xorg-video-nvidia libgl*-nvidia* libegl-nvidia* libgles-nvidia* libglx-nvidia* libxnvctrl0
Pin: version 550.*
Pin-Priority: 1001
EOF
sudo apt purge '~nnvidia' '~nlibnvidia'
sudo apt autoremove --purge
sudo apt install nvidia-driver nvidia-kernel-dkms
```
