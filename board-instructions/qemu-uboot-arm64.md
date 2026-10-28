## Before you start

- This image runs in QEMU (`virt` machine), not on hardware.
- The image is a `.qcow2` disk. U-Boot is the VM firmware: use the `*.u-boot.bin` file. The image also has it in `/usr/lib/linux-u-boot-*/u-boot.bin`.

## Installation

1. Start the VM:

```sh
qemu-system-aarch64 -machine virt -cpu cortex-a72 -m 2048 -nographic \
  -bios Armbian_*.u-boot.bin -nic user,model=virtio-net-pci \
  -drive if=none,media=disk,id=drive0,file=Armbian_*.img.qcow2,discard=unmap,detect-zeroes=unmap \
  -device virtio-blk-pci,drive=drive0,bootindex=0
```

2. On an arm64 host with KVM support, you can try `-accel kvm`.

## Serial console

- The console is `ttyAMA0`. With `-nographic`, it is in your terminal.
