## Before you start

Write Armbian to the eMMC of the JetHub H1 with Amlogic Burning Tool.

- Use the `.burn.img` file from the download. The normal `.img` file does not work with Burning Tool.
- Get Burning Tool from the [JetHome firmware portal](https://fw.jethome.com/browse/linux_controlles/). Install the CP210x USB driver.

## Installation

1. Hold the BOOT button. The button is in a hole in the case, between the Ethernet and microUSB ports.
2. Connect the controller to the computer with a USB cable. The cable supplies power.
3. Release the button after 1-2 seconds. Burning Tool shows "Connect success".
4. Select **File > Import image** and select the `.burn.img` file.
5. Click **Start**. If errors occur, clear **Erase flash** and **Erase bootloader**.
6. When Burning Tool shows "Burning successful", click **Stop**.

## Notes

- Press the BOOT button gently with a toothpick. Do not use a sharp tool.
- If flashing fails, use a USB 2.0 port on the computer.

## Rescue

Use this if the board does not boot after a write to eMMC or SPI.

1. Stop the boot ROM from reading the internal flash. Hold the recovery button,
   or short the eMMC clock pin to ground. Check the vendor documentation for the
   button on your board.
2. Connect the OTG port to the host and power on. The board enters USB boot mode.
3. Write the vendor firmware. Use the Amlogic USB Burning Tool on Windows, or
   [pyamlboot](https://github.com/superna9999/pyamlboot) on Linux.
4. Power off, remove the short, and boot from a microSD card.
