## Before you start

- Tinker Board (without eMMC) uses the normal microSD card flow.
- Tinker Board S boots from its eMMC before the microSD card.
- On Tinker Board S, write Armbian directly to the eMMC over the micro-USB port (USB Mass Storage mode).

## Install to internal storage

These steps apply to Tinker Board S. Remove all extension devices first.

1. Connect the board to a PC with a micro-USB cable. With ASUS Tinker OS on the eMMC, the eMMC shows as a USB drive.
2. Write the Armbian image to that USB drive with USBImager or Etcher.
3. Disconnect the cable and power on the board.

If the eMMC has no working ASUS U-Boot, start USB Mass Storage mode from a microSD card:

1. Write ASUS Tinker OS to a microSD card and insert it into the board.
2. Set the jumper to **Maskrom Mode**. This forces boot from the microSD card.
3. Connect the board to a PC with a micro-USB cable. The eMMC shows as a USB drive.
4. Write the Armbian image to that USB drive.
5. Disconnect the cable. Set the jumper to **Parking** (no function) mode.
6. Remove the microSD card and power on the board.

## Notes

- Vendor guide: [Tinker Board user manual](https://tinker-board.asus.com/download/User-Manual.pdf), section 4.
