## Before you start

- The Armbian image contains no bootloader. The board boots Armbian with the StarFive U-Boot in the QSPI flash.
- Firmware older than VF2_v2.11.5 fails to load the kernel from the microSD card.

## Installation

1. Update the QSPI firmware to VF2_v2.11.5 or newer. Follow **Updating SPL and U-Boot** in the [VisionFive 2 Quick Start Guide](https://doc-en.rvspace.org/VisionFive2/PDF/VisionFive2_QSG.pdf).
2. Set the boot mode switches to QSPI flash: RGPIO_0 = 0, RGPIO_1 = 0.

## Serial console

- The console is `ttyS0` at 115200 baud.
