# Pico SDK Prebuilt UF2s

This repository is used to provide pre-built UF2s of some of the universal [Pico Examples](https://github.com/raspberrypi/pico-examples). The available UF2s are:
- [`blink_universal.uf2`](https://github.com/raspberrypi/pico-sdk-prebuilts/releases/latest/download/blink_universal.uf2) - Blinks the LED on Pico-series and Pico W-series boards
- [`nuke_universal.uf2`](https://github.com/raspberrypi/pico-sdk-prebuilts/releases/latest/download/nuke_universal.uf2) - Erases the Flash on any RP-series microcontroller based boards. On Pico-series boards this will flash the LED when finished, and then on all boards it will reset back to `BOOTSEL` mode.
- [`hello_universal.uf2`](https://github.com/raspberrypi/pico-sdk-prebuilts/releases/latest/download/hello_universal.uf2) - Prints "Hello, world!" over USB and UART (using GPIO0 for UART TX, with baudrate 115200). On RP2350 based boards, it reboots between Arm and Risc-V architectures every 10s.

These can be dragged & dropped onto any RP2-series microcontroller based board, although the LED will only work on boards with the same LED GPIO as the Pico-series boards (GPIO 25).
