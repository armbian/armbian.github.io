## Before you start

- The module boots from its on-module eMMC. Factory eFuses select eMMC boot.
- The boot ROM does not start a bootloader from the microSD card. The U-Boot in the eMMC must load Armbian from the card.
- The module can also boot over USB in recovery mode. See the [Toradex documentation](https://developer.toradex.com/) for your carrier board.

## Notes

- Mainline U-Boot notes for this module: [Verdin iMX8M Mini](https://docs.u-boot.org/en/latest/board/toradex/verdin-imx8mm.html).
