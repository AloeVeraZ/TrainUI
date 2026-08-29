<div align="center">

# Train UI

### A live NYC train display I built in two sizes

[![Builds](https://img.shields.io/badge/Builds-XL_%2B_Mini-2563eb?style=flat-square)](#choose-a-version)
[![Data](https://img.shields.io/badge/Data-MTA_Realtime-111111?style=flat-square)](https://www.mta.info/developers)
[![Coverage](https://img.shields.io/badge/Coverage-Subway_%2B_SIR-6b7280?style=flat-square)](#what-both-versions-show)

<strong>Quick navigation:</strong><br>
[Overview](#overview) | [Choose a Version](#choose-a-version) | [Shared Features](#what-both-versions-show) | [Repository Contents](#repository-contents)

</div>

---

## Overview

I made Train UI so I could check the next trains without opening an app every time. You choose a train and station once, then leave the display running.

There are two versions. **Train UI XL** is the original Raspberry Pi build with a large color screen. **Train UI Mini** is the smaller ESP32 version with an e-paper screen. They use different hardware, but they show the same main information.

## Choose a version

| Train UI XL | Train UI Mini |
| --- | --- |
| [![Train UI XL placeholder](assets/images/train-ui-xl-placeholder.svg)](Train%20UI%20XL/) | [![Train UI Mini](assets/images/train-ui-mini.jpg)](Train%20UI%20Mini/) |
| 10.1-inch color display and Raspberry Pi Zero W | 2.13-inch e-paper display and ESP32-S3 |
| Shows the full dashboard, weather, and Raspberry Pi health | Smaller, cheaper, and easier to build |
| [Open the XL setup](Train%20UI%20XL/) | [Open the Mini setup](Train%20UI%20Mini/) |

## Hardware comparison

| | Train UI XL | Train UI Mini |
| --- | --- | --- |
| Display | 10.1-inch 1024 x 600 HDMI LCD | 2.13-inch 122 x 250 e-paper |
| Controller | Original Raspberry Pi Zero W | ESP32-S3 built into the display |
| Software | Raspberry Pi OS and Python | Arduino firmware |
| Setup | Flash Raspberry Pi OS and run one command | Upload the Arduino sketch |
| Best for | A permanent display that is easy to read across a room | A small desk display with very little hardware |

## What both versions show

- The next arrivals in both directions
- Train and station selection during setup
- MTA service status and alerts
- Local weather or temperature
- Time and connection status
- Live MTA data without an API key

## Repository contents

```text
.
├── assets/          # Photos used by this README
├── Train UI XL/     # Raspberry Pi code, installer, tests, and image tools
├── Train UI Mini/   # ESP32-S3 firmware and Mini setup
└── README.md
```

Open the folder for the version you want to build. Each one has its own parts list and setup instructions.
