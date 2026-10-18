## Before you start

The CB2 boots from eMMC before the microSD card. To boot from microSD, erase the eMMC first.

## Installation

1. Set the USBOTG and RPIBOOT DIP switches on the carrier board to ON. The CB2 enters BOOT mode.
2. Connect the USB OTG port to the computer. Do not insert a microSD card.
3. If the eMMC shows as a USB mass storage device, erase it with a disk tool.
4. If it shows as a LOADER device, erase it with RKDevTool.
5. Set the DIP switches back to OFF.
6. Write the image to a microSD card. Insert it and power on.

## Install to internal storage

You can also write the image directly to the eMMC in BOOT mode. Use balenaEtcher for a mass storage device. Use RKDevTool with **Write by Address** for a LOADER device. RKDevTool does not accept `.xz` files.
