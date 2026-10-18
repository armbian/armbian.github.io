## Serial console

The board has no accessible UART. Connect a USB cable to the OTG USB-C port. The console is the USB gadget serial port `ttyGS0`.

## Notes

- The OTG USB-C port gives no power to USB devices by default. While the port gives power, the battery does not charge from the DC port.
- To power a bus-powered USB device on the OTG port, run `sudo rgds-otg on`.
- To charge the battery again, run `sudo rgds-otg off`.
- A self-powered USB hub works in both states.
