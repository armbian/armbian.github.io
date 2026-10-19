## Before you start

The board has no microSD slot. Write Armbian to the eMMC with OOWOW, the Khadas installer in SPI flash. The Armbian image is in OOWOW format.

## Installation

1. Connect an HDMI display and a USB keyboard.
2. Hold the **FUNCTION** button and short press **RESET**. OOWOW starts.
3. Select **Write Image to eMMC**.
4. Select the Armbian image from the download server or from a USB drive.
5. Reboot when the write is complete.

## Notes

- OOWOW also has a web interface and a shell API. See the [Khadas OOWOW guide](https://docs.khadas.com/products/sbc/edge2/install-os/install-os-into-emmc-via-oowow).
- To enter MaskROM mode, press **FUNCTION** 3 times in 2 seconds.
