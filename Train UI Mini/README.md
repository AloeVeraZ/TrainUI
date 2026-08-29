<div align="center">

# Train UI Mini

### The small e-paper version of my NYC train display

[![Hardware](https://img.shields.io/badge/Hardware-ESP32--S3-111111?style=flat-square&logo=espressif&logoColor=white)](https://www.amazon.com/dp/B0H25DMJ8M)
[![Display](https://img.shields.io/badge/Display-2.13%22_E--Paper-6b7280?style=flat-square)](#parts)
[![Data](https://img.shields.io/badge/Data-MTA_Realtime-2563eb?style=flat-square)](https://www.mta.info/developers)
[![Setup](https://img.shields.io/badge/Setup-Arduino_IDE-f59e0b?style=flat-square&logo=arduino&logoColor=white)](#setup)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

[![Train UI Mini](assets/train-ui-mini-desk.png)](assets/train-ui-mini-desk.png)

<strong>Quick navigation:</strong><br>
[Overview](#overview) | [Parts](#parts) | [Setup](#setup) | [Controls](#controls) | [Project Files](#project-files)

</div>

---

## Overview

I made Train UI Mini as a cheaper and simpler version of [Train UI XL](../Train%20UI%20XL/). Instead of a Raspberry Pi and HDMI screen, it uses one ESP32-S3 e-paper board and a USB-C cable.

It shows three arrivals in both directions, MTA service status, Coney Island temperature, time, and connection status. During setup, you choose a train and then any station served by it. You do not need to enter MTA stop IDs or use an API key.

## Parts

| Qty. | Part | Link |
| --- | --- | --- |
| 1 | Elecrow CrowPanel ESP32-S3 2.13-inch e-paper display | [Amazon](https://www.amazon.com/dp/B0H25DMJ8M) |
| 1 | USB-C cable | Any data cable that works with the board |
| Optional | 3D-printed desk case | [Printables](https://www.printables.com/model/1566902-case-for-crowpanel-213-epaper/related) |

The case is not part of this repository. You can use the bare board, print the linked case, or make your own.

## Setup

### 01 / Arduino IDE

Install **esp32 by Espressif Systems** in Arduino IDE, then open:

```text
TrainUIMiniCode/TrainUIMiniCode.ino
```

Use these board settings:

| Setting | Value |
| --- | --- |
| Board | ESP32S3 Dev Module |
| Flash Size | 8MB (64Mb) |
| PSRAM | OPI PSRAM |
| USB CDC On Boot | Enabled |

Select the board's USB port and upload the sketch.

### 02 / First boot

1. Connect a phone or computer to the Wi-Fi network **TrainUIMini**.
2. Enter password **TRAINUI1**.
3. Open `http://192.168.4.1`.
4. Enter your normal Wi-Fi information.
5. Choose a train and station.
6. Save the setup and let the board restart.

The Wi-Fi information and train selection stay saved on the ESP32.

## Controls

| Control | What it does |
| --- | --- |
| Menu | Opens Wi-Fi, train, and station setup again |
| Dial press | Switches between live data and offline sample data |
| Back | Refreshes the live information |

Offline mode is useful for testing the screen without internet. The display shows `ONLINE` or `OFFLINE` so you know which mode is running.

## Data

Arrivals and alerts come from the MTA's public realtime feeds. Temperature comes from Open-Meteo using Coney Island coordinates. The board connects to both services directly, so there is no phone app, separate server, account, or API key.

## Project files

```text
.
├── assets/                  # Mini photos
├── TrainUIMiniCode/
│   ├── SubwayCatalog.h      # Train and station catalog
│   └── TrainUIMiniCode.ino  # Main Arduino firmware
├── LICENSE
└── README.md
```

## License

Train UI Mini is available under the [MIT License](LICENSE).
