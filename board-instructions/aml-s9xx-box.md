## Before you start

- The box starts the vendor u-boot on eMMC. The vendor u-boot then chain-loads `u-boot.ext` from the microSD card.
- If the box ran another distribution (for example CoreELEC), restore the original Android firmware first.

## Installation

1. On the BOOT partition, open `extlinux/extlinux.conf`. Change the `fdt` line to the DTB for your box. The DTBs are in `dtb/amlogic/`.
2. On the BOOT partition, copy the u-boot file for your SoC to `u-boot.ext`. Keep the original file.
   - `u-boot-s905`: S905
   - `u-boot-s905x-s912`: S905X, S905W, S905D, S905L, S805X, S912
   - `u-boot-s905x2-s922`: S905X2, S922X
   - `u-boot-s905x3`: S905X3
3. Insert the card. Push the reset button inside the AV jack with a toothpick.
4. Hold the button and connect power. Release the button after some seconds.
5. If Android starts, repeat steps 4 and 5 with a longer or shorter hold time.

## Install to internal storage

- The image has no `armbian-install`. It would make the box unbootable.
- Installation to eMMC can brick the box. Keep the Android firmware and the Amlogic USB Burning Tool ready for recovery.
- Installation to eMMC does not work on S905 boxes.

1. Make a backup of the eMMC.
2. Run `/root/install-aml.sh`.
