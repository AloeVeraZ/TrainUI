<div align="center">

# Train UI XL

### The original full-size NYC train display

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/software/)
[![Code](https://img.shields.io/badge/Code-Python-3776ab?style=flat-square&logo=python&logoColor=white)](timertest.py)
[![Data](https://img.shields.io/badge/Data-MTA_Realtime-2563eb?style=flat-square)](https://www.mta.info/developers)

[![Train UI XL photo placeholder](../assets/images/train-ui-xl-placeholder.svg)](../assets/images/train-ui-xl-placeholder.svg)

<strong>Quick navigation:</strong><br>
[Overview](#overview) | [Parts](#parts) | [Setup](#setup) | [Change the Train or Station](#change-the-train-or-station) | [Useful Commands](#useful-commands)

</div>

---

## Overview

Train UI XL is the first version of Train UI. I built it around an original Raspberry Pi Zero W and a 10.1-inch HDMI screen so I could see arrivals, service changes, weather, time, and the Pi's health from across the room.

The display starts by itself when the Pi boots. The installer handles the Python libraries, screen rotation, automatic startup, Wi-Fi watchdog, and the train and station menu. It uses public MTA and Open-Meteo data, so it does not need an API key.

## Parts

| Qty. | Part | Notes |
| --- | --- | --- |
| 1 | Original Raspberry Pi Zero W | The tested board. It only supports 2.4 GHz Wi-Fi. |
| 1 | 10.1-inch 1024 x 600 HDMI display | I used the [HAMTYSAN B0FMF3RTPC](https://www.amazon.com/dp/B0FMF3RTPC). |
| 1 | MicroSD card | Large enough for Raspberry Pi OS with Desktop. |
| 1 | HDMI adapter and cable | Match the ports on the Pi and display. |
| 1 | Power supply | Use the correct supply for the Pi and screen. |

Other Raspberry Pis and HDMI screens may work, but the software and enclosure were made around the parts above.

## What it shows

- The next arrivals in both directions
- The selected station, borough, and train badge
- MTA service alerts for the train or station
- NYC weather, wind, and humidity
- Time and date
- CPU temperature, RAM, storage, load, uptime, IP address, and network speed

The setup menu includes the numbered and lettered subway lines, the three subway shuttles, and Staten Island Railway. LIRR and Metro-North are not included.

## Setup

### 01 / Flash Raspberry Pi OS

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) and install the current **Raspberry Pi OS (32-bit) with Desktop** image.

In the Imager settings:

- Add your Wi-Fi information.
- Enable SSH.
- Create a username and password.
- Set the hostname, locale, and timezone you want.

Connect the HDMI screen before the first Train UI boot. The reference enclosure uses 270-degree rotation.

### 02 / Connect with SSH

```bash
ssh YOUR_USERNAME@YOUR_PI_HOSTNAME.local
```

Use the Pi's IP address instead if the `.local` hostname does not work.

### 03 / Run the installer

Run this as the normal Pi user. Do not add `sudo` before it.

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/installer/install.sh | bash
```

Choose a train, then choose a station. The installer finishes the setup and reboots the Pi. Train UI starts automatically after the desktop loads.

## Change the train or station

SSH into the Pi and run the same command again:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/installer/install.sh | bash
```

Answer `n` when it asks if you want to keep the current choice. The same command also updates the code and Python environment. Your selection stays in `~/.config/trainui/config.json`.

## Useful commands

View the log:

```bash
tail -f "$HOME/TrainUI/Train UI XL/trainui.log"
```

Restart the display without rebooting:

```bash
pkill -f timertest.py || true
"$HOME/TrainUI/Train UI XL/run_trainui.sh" &
```

Check the Wi-Fi watchdog:

```bash
systemctl status trainui-connectivity.timer
```

## Troubleshooting

| Problem | What to check |
| --- | --- |
| SSH does not connect | Make sure SSH was enabled and try the Pi's IP address. |
| Nothing opens after reboot | Make sure Raspberry Pi OS reaches the desktop, then check the log above. |
| Arrivals are unavailable | Check the internet connection. Some trains do not run at every station all day. |
| Wi-Fi keeps disconnecting | Make sure the original Pi Zero W is using a 2.4 GHz network. |
| Screen rotation is wrong | Change the rotation in `run_trainui.sh`, or rerun the installer after mounting the screen at 270 degrees. |
| Screen still turns off | Disable any sleep timer or eco mode built into the monitor itself. |

## Development

Run these commands from the `Train UI XL/` folder:

```bash
python3 -m unittest discover -s tests -v
python3 tests/validate_live_feeds.py
python3 timertest.py --smoke-test
```

## Repository contents

```text
.
├── image/             # Raspberry Pi image build files
├── installer/         # One-command installer and route setup
├── tests/             # Catalog, display, and installer checks
├── requirements.txt
├── timertest.py       # Main Train UI XL program
└── README.md
```
