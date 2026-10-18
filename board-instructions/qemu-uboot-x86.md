## Before you start

- This image runs in QEMU (`q35` machine), not on hardware.
- The image is a `.qcow2` disk. U-Boot is the VM firmware: use the `*.u-boot.rom` file. The image also has it in `/usr/lib/linux-u-boot-*/u-boot.rom`.

## Installation

1. Start the VM on a Linux x86 host with KVM:

```sh
qemu-system-x86_64 -accel kvm -machine q35,vmport=off -smp 8 -m 2048 -nographic \
  -bios Armbian_*.u-boot.rom -nic user,model=virtio-net-pci \
  -device virtio-blk-pci,drive=drive0,bootindex=0 \
  -drive if=none,media=disk,id=drive0,file=Armbian_*.img.qcow2,discard=unmap,detect-zeroes=unmap
```

2. On macOS, remove `-accel kvm`.

## Serial console

- The console is `ttyS0`. With `-nographic`, it is in your terminal.
