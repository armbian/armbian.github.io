## Before you start

- The board has no microSD slot. The OS runs from the onboard eMMC.
- Write Armbian to the eMMC with the iagent Reflash tool. Reflash runs from a USB drive.
- The board has 3 buttons: FEL, BOOT and RESET (RST).

## Installation

1. Write the [Reflash image](https://github.com/intelligent-agent/Reflash/releases) to a USB drive of 4 GB or more.
2. Insert the USB drive into a USB port on the board.
3. Boot Reflash:
   - If Rebuild or Refactor is on the eMMC, reboot the board with the USB drive inserted.
   - On first use, boot through FEL mode. Follow [Entering FEL mode](https://wiki.iagent.no/wiki/Reflash#Entering_FEL_mode).
4. Open `http://recore.local` in a browser.
5. Select **Upload file** and upload the Armbian image.
6. Flash the image to the eMMC. This takes 3 to 4 minutes.
7. Remove the USB drive and reboot the board.

## Serial console

- Connect the USB-C port to the PC. The console shows as `/dev/ttyACM0`.
