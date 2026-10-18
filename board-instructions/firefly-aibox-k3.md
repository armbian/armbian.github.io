## Before you start

- The AIBOX-K3 starts the factory U-Boot from SPI NOR flash. The Armbian image does not contain U-Boot. Do not erase the SPI NOR flash.
- Armbian runs from the UFS storage. Write the boot and root partitions of the image to UFS with the Firefly TitanFlasher tool.
- See the [Firefly firmware upgrade guide](https://wiki.t-firefly.com/en/AIBOX-K3/upgrade_firmware.html).

## Installation

1. Connect the USB-C port to the computer. Connect the serial console.
2. Run `reboot`. Hold the `s` key while U-Boot starts.
3. At the U-Boot prompt, run `fastboot 0`.
4. Write the partitions to UFS with TitanFlasher.

## Serial console

- Use 115200 baud on `ttyS0`.
