## Before you start

The board has no microSD slot. Armbian writes to the onboard eMMC in EDL (Emergency Download) mode.

- Use [Armbian Imager](https://imager.armbian.com/). It writes the image over EDL. No other tool is necessary.
- On Linux, give your user access to USB ID `05c6:9008` and blacklist the `qcserial` driver. See [Writing the image](https://docs.armbian.com/getting-started/writing-the-image/#qualcomm).

## Installation

1. Power off the board.
2. Put a jumper on the **JCTL** pins.
3. Connect the USB-C port to your computer.
4. Open Armbian Imager, select the board and the image, and write it.
5. Remove the JCTL jumper. Disconnect and connect USB-C again to boot.

On the first boot, the root filesystem grows to fill the eMMC.

## Serial console

- The UART is on the JCTL header, `ttyMSM0` at 115200 baud.
- The UART uses 1.8 V logic. Do not use a 3.3 V or 5 V adapter.

## Rescue

Use this if the board does not boot after a write to eMMC.

1. Power off the board and put a jumper on the **JCTL** pins.
2. Connect the USB-C port to your computer. The board starts in EDL (Emergency
   Download) mode, whatever the eMMC holds.
3. Write the image again with [Armbian Imager](https://imager.armbian.com/).
4. Remove the JCTL jumper. Disconnect and connect USB-C again.

EDL mode is in the boot ROM. A broken eMMC image cannot stop it.
