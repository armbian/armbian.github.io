## Before you start

This image is for these boards: NanoPi R6S, R6C, M6, M6V2, NanoPC T6, T6-LTS and T6-LTS-Plus.

## Notes

- The U-Boot in this image detects the board model. It then loads the matching device tree.
- Other U-Boot builds cannot detect the model. The kernel then uses the NanoPi R6S device tree.
- If the board boots another U-Boot, run `armbian-install`. Update the bootloader on the boot device.
