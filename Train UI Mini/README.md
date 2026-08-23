<div align="center">

# Train UI Mini

### NYC arrivals on one small e-paper screen

[![Hardware](https://img.shields.io/badge/Hardware-ESP32--S3-111111?style=flat-square&logo=espressif&logoColor=white)](https://www.amazon.com/dp/B0H25DMJ8M)
[![Display](https://img.shields.io/badge/Display-2.13%22_E--Paper-6b7280?style=flat-square)](#what-you-need)
[![Data](https://img.shields.io/badge/Data-MTA_Realtime-2563eb?style=flat-square)](https://www.mta.info/developers)
[![Setup](https://img.shields.io/badge/Setup-Arduino_IDE-f59e0b?style=flat-square&logo=arduino&logoColor=white)](#uploading-the-code)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

Three arrivals each way · service status · Coney Island temperature

<strong>Quick navigation:</strong><br>
[Trains & Stations](#trains-and-stations) | [Hardware](#what-you-need) | [Upload](#uploading-the-code) | [First Setup](#first-setup) | [Controls](#controls)

</div>

> **Project image placeholder:** Add the finished display photo here as `train-ui-mini.jpg`, then replace this note with `![Train UI Mini running](train-ui-mini.jpg)`.

Train UI Mini is the cheaper, simpler version of [Train UI](../Train%20UI/). It shows live NYC arrivals, service status, Coney Island temperature, time, and connection state on one screen.

The regular build uses a Raspberry Pi and a larger HDMI display. The Mini only needs the CrowPanel, a USB-C cable, and the Arduino code in this folder.

## Trains and stations

During setup, you choose a train and then choose any station served by it. The station list automatically changes to match the selected train, so you do not need to find or enter MTA stop IDs yourself.

The included catalog covers NYC Subway service, the subway shuttles, and Staten Island Railway. No train or station is selected by default, and you can reopen setup later if you want to change either one.

## What you need

- [Elecrow CrowPanel ESP32-S3 2.13-inch e-paper display](https://www.amazon.com/dp/B0H25DMJ8M)
- USB-C cable
- Arduino IDE
- Wi-Fi for live arrivals and temperature
- Optional 3D-printed case

Unlike the regular Train UI build, Train UI Mini is just the e-paper board and firmware. A custom enclosure is not included, so you can use the bare display or print your own case.

The case currently used for the desk build is this [CrowPanel 2.13-inch e-paper case on Printables](https://www.printables.com/model/1566902-case-for-crowpanel-213-epaper/related). It is not part of this repository, but it fits the board and is the recommended option if you do not want to design one.

## Uploading the code

1. Install **esp32 by Espressif Systems** in Arduino IDE.
2. Open `TrainUIMiniCode/TrainUIMiniCode.ino`.
3. Select **ESP32S3 Dev Module**.
4. Set **Flash Size** to **8MB (64Mb)**.
5. Set **PSRAM** to **OPI PSRAM**.
6. Set **USB CDC On Boot** to **Enabled**.
7. Select the board's USB port and upload.

## First setup

After uploading:

1. Connect a phone or computer to Wi-Fi network **TrainUIMini**.
2. Use password **TRAINUI1**.
3. Open `http://192.168.4.1`.
4. Enter your normal Wi-Fi information.
5. Choose your train and station.
6. Save and let the board restart.

The selection and Wi-Fi information are saved on the ESP32. Press **Menu** to reopen setup later.

## Controls

| Control | Action |
|---|---|
| Menu | Reopen Wi-Fi, train, and station setup |
| Dial press | Switch between live data and offline sample data |
| Back | Refresh live information immediately |

Offline mode lets you test the interface without internet. The screen clearly shows `ONLINE` or `OFFLINE`.

## Data

Train arrivals and alerts come directly from the MTA's public realtime feeds. Temperature comes from Open-Meteo using Coney Island coordinates. No API key, account, phone app, or separate server is required.

## Project files

All firmware is inside `TrainUIMiniCode/`. Open `TrainUIMiniCode.ino` in Arduino IDE, or open the entire code folder if you use PlatformIO.

## License

Train UI Mini is available under the [MIT License](LICENSE).
