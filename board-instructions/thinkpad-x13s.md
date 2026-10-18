## Before you start

The laptop boots Armbian from a USB drive. Set the firmware first:

1. Update the BIOS with the Lenovo BIOS Update Utility in Windows.
2. Press **F1** at power on to open the BIOS setup.
3. Go to **Config** > **Linux** > **Linux Boot (Beta)**. Set it to on.
4. Go to **Security** > **Secure Boot** > **Secure Boot**. Set it to off.

Windows asks for the BitLocker recovery key after you disable Secure Boot.

## Installation

1. Write the image to a USB drive.
2. Connect the USB drive directly to a USB port. Some laptops do not boot from a hub.
3. Press **F12** at power on. Select the USB drive.
