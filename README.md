<div align="center">

# Train UI

### One NYC departure board · two different builds

[![Projects](https://img.shields.io/badge/Builds-XL_%2B_Mini-2563eb?style=flat-square)](#choose-a-build)
[![Data](https://img.shields.io/badge/Data-MTA_Realtime-111111?style=flat-square)](https://www.mta.info/developers)
[![Coverage](https://img.shields.io/badge/Coverage-Subway_%2B_SIR-6b7280?style=flat-square)](#shared-features)

Live arrivals · service alerts · weather · one quick look before leaving

<strong>Quick navigation:</strong><br>
[Choose a Build](#choose-a-build) | [Compare Hardware](#hardware-comparison) | [Shared Features](#shared-features) | [XL Setup](Train%20UI%20XL/) | [Mini Setup](Train%20UI%20Mini/)

</div>

---

Train UI puts the useful part of a transit app on a screen that is already sitting there. Pick a train and station once, then look over whenever you need the next arrivals.

There are two builds in this repo. **Train UI XL** is the larger Raspberry Pi dashboard. **Train UI Mini** puts the same idea on a small ESP32 e-paper display. XL shows more; the Mini is cheaper and much easier to start.

## Choose a build

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Train UI XL</h3>
      <p><strong>10.1-inch color display · Raspberry Pi Zero W</strong></p>
      <p>The original full-size build. It has room for arrivals, service information, weather, time, and Raspberry Pi health on one dashboard.</p>
      <p><strong>Best for:</strong> a larger permanent display that can be read from across a room.</p>
      <p><strong><a href="Train%20UI%20XL/">Hardware, installer, and setup →</a></strong></p>
    </td>
    <td width="50%" valign="top">
      <h3>Train UI Mini</h3>
      <p><strong>2.13-inch e-paper · ESP32-S3</strong></p>
      <p>A one-page desk version. The controller, Wi-Fi, buttons, and screen are already built into the CrowPanel.</p>
      <p><strong>Best for:</strong> a lower-cost first build with no Raspberry Pi or Linux setup.</p>
      <p><strong><a href="Train%20UI%20Mini/">Arduino upload and setup →</a></strong></p>
    </td>
  </tr>
</table>

## Hardware comparison

| | Train UI XL | Train UI Mini |
|---|---|---|
| Display | 10.1-inch 1024×600 color HDMI LCD | 2.13-inch 122×250 black-and-white e-paper |
| Computer | Raspberry Pi Zero W | ESP32-S3 built into the display |
| Software | Raspberry Pi OS and Python | Arduino firmware |
| Install | Flash Raspberry Pi OS, connect through SSH, run the installer | Open the sketch in Arduino IDE and upload |
| Build | Pi, screen, storage, cables, power, and printed enclosure | CrowPanel, USB-C cable, and optional printed case |
| Main tradeoff | More hardware and setup | Smaller screen and slower refresh |

The XL build is easier to read and has more room to grow. The Mini removes most of the hardware and setup: order the screen, print a case if you want one, and upload the Arduino code.

## Shared features

Both versions:

- Let you choose a train and then any station served by it.
- Show the next arrivals in both directions.
- Use public MTA realtime feeds with no API key.
- Include service status, local weather or temperature, and connection state.
- Save the selected train and station for the next boot.
- Work as passive displays instead of another phone app.

## Repository layout

```text
TrainUI/
├── Train UI XL/     # Raspberry Pi app, installer, tests, and image tooling
└── Train UI Mini/   # ESP32-S3 e-paper version and Arduino firmware
```

Each build has its own README. Open the folder for the hardware you want to use.
