## Notes

- Use a 12 V USB-C power adapter.
- The board boots from USB, microSD, NVMe, eMMC and UFS, in this order.
- The UEFI firmware (EDK2) is in SPI NOR flash. To update it from Armbian, run:

```sh
sudo armbian-install bootloader --target mtd
```

The command saves the old SPI NOR contents to `/var/backups` first.

## Rescue

Use this if the board does not boot.

1. If the UEFI firmware still starts, boot from USB or a microSD card. Both come
   before NVMe, eMMC and UFS in the boot order. Restore the previous SPI NOR
   contents from `/var/backups`.
2. If the UEFI firmware does not start, put the board in EDL (Emergency
   Download) mode and write the firmware with
   [qdl](https://github.com/linux-msm/qdl).

`armbian-install bootloader --target mtd` saves the old SPI NOR contents to
`/var/backups` before it writes. Keep that copy.
