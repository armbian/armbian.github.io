## Before you start

Write Armbian to the eMMC of the JetHub D2 with Amlogic Burning Tool.

- Use the `.burn.img` file from the download. The normal `.img` file does not work with Burning Tool.
- Get Burning Tool from the [JetHome firmware portal](https://fw.jethome.com/browse/linux_controlles/). Install the CP210x USB driver.

## Installation

1. Put the controller in bootloader mode. See the [JetHome Burning Tool guide](https://docs.jethome.com/en/controllers/linux/howto/amlogic/burning_tool.html).
2. Connect the controller to the computer with a USB cable. Burning Tool shows "Connect success".
3. Select **File > Import image** and select the `.burn.img` file.
4. Click **Start**. If errors occur, clear **Erase flash** and **Erase bootloader**.
5. When Burning Tool shows "Burning successful", click **Stop**.

## Notes

If flashing fails, use a USB 2.0 port on the computer.
