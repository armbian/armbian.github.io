## Notes

- Use a 12 V USB-C power adapter.
- The board boots from USB, microSD, NVMe, eMMC and UFS, in this order.
- The UEFI firmware (EDK2) is in SPI NOR flash. To update it from Armbian, run:

```sh
sudo armbian-install bootloader --target mtd
```

The command saves the old SPI NOR contents to `/var/backups` first.
