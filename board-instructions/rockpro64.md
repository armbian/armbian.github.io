## Install to internal storage

The RK3399 cannot boot from NVMe. Put the bootloader in SPI flash and the system on NVMe:

1. Boot Armbian from the microSD card.
2. Run `armbian-install`.
3. Select the NVMe disk and **Boot from SPI/MTD flash, system on this disk**.

## Notes

- If the eMMC and the microSD card both hold a bootloader, the board starts the eMMC. Fit jumper SW4 (between the eMMC socket and the SPI chip) to disable the eMMC.
- If a bad SPI bootloader blocks boot, connect pin 23 (CLK) to pin 25 (GND) on the Pi-2 header during boot. The board then skips the SPI flash.

## Rescue

Use this if the board does not boot after a write to SPI or eMMC.

1. Put the board in MaskROM mode. Hold the MaskROM button, or short the flash
   CLK pin to ground. Connect the OTG port to a Linux host and power on.
2. Erase the broken flash:
```sh
sudo rkdeveloptool ld
sudo rkdeveloptool db <loader for your SoC>
sudo rkdeveloptool ef
```
3. Power off, release the button or remove the short, and boot from a microSD card.

Loaders are in [armbian/rkbin](https://github.com/armbian/rkbin).
See [Writing the image](https://docs.armbian.com/getting-started/writing-the-image/#rockchip).
