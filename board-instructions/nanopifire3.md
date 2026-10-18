## Notes

- Armbian uses 4 of the 8 CPU cores. The bootloader leaves the second CPU cluster non-coherent.
- A warm `reboot` can hang. Disconnect and connect the power supply to restart the board.
