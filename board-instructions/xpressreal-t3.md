## Before you start

- Power the board through the USB-C port with 12 V. Use a USB PD power supply that supports 12 V and more than 2 A.
- The onboard eMMC has no factory firmware. Boot Armbian from a microSD card first.

## Serial console

- The console is `ttyS0` at 460800 baud.

## Rescue

Use this if the board does not boot after a write to eMMC.

1. Write a working Armbian image to a microSD card.
2. Insert the card and power the board through the USB-C port with 12 V. The
   board boots the card.
3. Rewrite the eMMC from the running system, or erase it. Identify the
   eMMC with `lsblk`; it is the `mmcblk*` device that is not the card you
   booted from:
```sh
sudo blkdiscard -f /dev/mmcblkX
```
