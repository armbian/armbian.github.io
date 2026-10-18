## Before you start

- A slide switch on the board selects the RISC-V core or the ARM core.
- Set the switch to **ARM** for this image.
- If the board does not start, check the switch first. On the serial console, the first boot line starts with `B` for the ARM core.

## Install to internal storage

`armbian-install` does not support the eMMC on this board. The eMMC bootloader goes into a hardware boot partition.

1. Boot Armbian from the microSD card.
2. Copy the Armbian image file to the board.
3. Write the image and the eMMC bootloader:

```sh
sudo sophgo-emmc-install Armbian_*.img.xz
```

4. Power off the board.
5. Remove the microSD card. The board boots from the card when a card is present.
6. Power on the board.

## Rescue

Use this if the board does not boot after a write to eMMC.

1. Insert a microSD card with a working Armbian image. The board boots the card
   when a card is present, whatever the eMMC holds.
2. Run `sophgo-emmc-install` again, or erase the eMMC. Identify it with
   `lsblk`; it is the `mmcblk*` device that is not the card you booted
   from:
```sh
sudo blkdiscard -f /dev/mmcblkX
```
3. Power off and remove the microSD card.

Check the ARM/RISC-V slide switch first. A wrong switch position looks like a
dead board.
