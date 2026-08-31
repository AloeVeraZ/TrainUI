<div align="center">

# Train UI XL

### The original full-size NYC train display

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/software/)
[![Code](https://img.shields.io/badge/Code-Python-3776ab?style=flat-square&logo=python&logoColor=white)](timertest.py)
[![Data](https://img.shields.io/badge/Data-MTA_Realtime-2563eb?style=flat-square)](https://www.mta.info/developers)

[![Train UI XL photo placeholder](../assets/images/train-ui-xl-placeholder.svg)](../assets/images/train-ui-xl-placeholder.svg)

<strong>Quick navigation:</strong><br>
[Overview](#overview) | [Parts](#parts) | [Assembly Guide](Assembly%20Guide/) | [Setup](#setup) | [Change the Train or Station](#change-the-train-or-station) | [Useful Commands](#useful-commands)

</div>

---

## Overview

Train UI XL is the first version of Train UI. I built it around an original Raspberry Pi Zero W and a 10.1-inch HDMI screen so I could see arrivals, service changes, weather, time, and the Pi's health from across the room.

The display starts by itself when the Pi boots. The installer handles the Python libraries, screen rotation, automatic startup, Wi-Fi recovery and setup, and the train and station menu. It uses public MTA and Open-Meteo data, so it does not need an API key.

> [!WARNING]
> **This build requires soldering and wire stripping.** Cut the USB-C end off the USB-C-to-Micro-USB adapter lead, keep the Micro-USB plug, and feed the cut end through the small opening in the printed back piece before soldering—the molded Micro-USB plug will not fit through that opening. Identify and verify 5V and ground with a multimeter, solder red to `V` and black to `G` on the loose USB-C socket board, then bolt the board into the back piece. Keep all power disconnected while working, insulate unused conductors, and check polarity and shorts before plugging anything in.
>
> The order matters. Feed the cable through the printed back piece, solder it to the socket board, and only then bolt the board in place. The finished wiring traps that printed piece in the assembly, so changing the back later requires desoldering the cable. I designed it this way so the USB-C port can sit recessed and flush with the outside of the enclosure instead of sticking out.

## Parts

This is the bill of materials for the complete XL build. The Pi, screen, and MicroSD card are the three main electronic parts. The other items route power and video through the enclosure and hold the printed pieces together. I will add the exact Pi, display, MicroSD, and power-supply listings when those choices are finalized.

| Qty. | Core part | What it does |
| ---: | --- | --- |
| 1 | Original Raspberry Pi Zero W | Runs Train UI XL. This is the board the software and enclosure are built around, and it needs a 2.4 GHz Wi-Fi network. |
| 1 | 10.1-inch 1024 × 600 HDMI display | Shows the full dashboard in portrait orientation. The enclosure dimensions are based on this screen class. |
| 1 | MicroSD card | Holds Raspberry Pi OS, Train UI XL, its configuration, and its log. |
| 1 | Correct power supply | Feeds the finished USB-C inlet with enough stable 5V power for the installed electronics. A weak supply can cause crashes or random freezes. |

### Cables, mounting hardware, and enclosure parts

The photos below are stored in this repository as visual references. The product name still links to the original listing, but the photo will remain here if that listing disappears.

<table>
  <tr>
    <td width="50%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0G5YZJLVZ"><img src="Assembly%20Guide/images/parts/usb-c-to-micro-usb-adapter.jpg" width="240" alt="USB-C female to Micro-USB male adapter cable"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0G5YZJLVZ">USB-C to Micro-USB adapter lead</a></strong><br>
      One lead from the four-pack becomes the internal Pi power harness. Cut off its USB-C end, keep the Micro-USB male end, strip it, and solder the verified 5V and ground wires to the panel-mount socket board.
    </td>
    <td width="50%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0CNGV7FQJ"><img src="Assembly%20Guide/images/parts/angled-mini-hdmi-cable.jpg" width="240" alt="Angled HDMI to mini-HDMI cable"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0CNGV7FQJ">90-degree HDMI to mini-HDMI cable</a></strong><br>
      Carries video from the Pi Zero W's mini-HDMI port to the display while keeping the cable bend compact inside the enclosure.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0D5V3TZLB"><img src="Assembly%20Guide/images/parts/heat-set-inserts.jpg" width="240" alt="M2 through M5 heat-set insert kit"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0D5V3TZLB">M2–M5 heat-set inserts</a></strong><br>
      Melt into the printed parts to add durable metal threads anywhere the enclosure needs to be opened and closed more than once.
    </td>
    <td width="50%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0F3WVBGCP"><img src="Assembly%20Guide/images/parts/usb-c-panel-mount.jpg" width="240" alt="USB-C female panel-mount socket boards"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0F3WVBGCP">USB-C female panel-mount socket board</a></strong><br>
      Becomes the finished power inlet. Keep it loose while soldering the cable that has already been fed through the printed back, then bolt its black plate into place so the connector sits recessed and flush.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0F87W7P59"><img src="Assembly%20Guide/images/parts/micro-usb-cable.jpg" width="240" alt="Short 90-degree Micro-USB male-to-male cable"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0F87W7P59">Short 90-degree Micro-USB cable</a></strong><br>
      Handles the compact internal Micro-USB power connection without leaving a long cable loop inside the printed shell.
    </td>
    <td width="50%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0FF4TDYKZ"><img src="Assembly%20Guide/images/parts/countersunk-fasteners.jpg" width="240" alt="Countersunk M2, M2.5, and M3 fastener assortment"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0FF4TDYKZ">Countersunk M2, M2.5, and M3 fasteners</a></strong><br>
      Hold low-profile parts where a flat screw head needs to finish level with the printed surface.
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0FGJ9FRGQ"><img src="Assembly%20Guide/images/parts/m3-fasteners.jpg" width="240" alt="M3 socket-head screw, nut, and washer assortment"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0FGJ9FRGQ">M3 socket-head fasteners</a></strong><br>
      Four M3 × 25 mm screws close the main enclosure through the M3 heat-set inserts; the assortment also provides reusable nuts and washers.
    </td>
    <td width="50%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B07ZH9GJWP"><img src="Assembly%20Guide/images/parts/self-tapping-screws.jpg" width="240" alt="Small black self-tapping screw assortment"></a><br>
      <strong><a href="https://www.amazon.com/dp/B07ZH9GJWP">Small self-tapping screws</a></strong><br>
      Secure light internal parts directly to printed plastic where a heat-set insert is unnecessary.
    </td>
  </tr>
</table>

### Tools and consumables

- Soldering iron, solder, and a safe iron stand
- Wire cutters and wire strippers
- Multimeter for continuity, polarity, 5V, and ground checks
- Heat-shrink tubing or another proper way to insulate every exposed conductor
- Heat-set insert tip and the matching screwdrivers or hex keys

Other Raspberry Pis and HDMI screens may run the software, but the enclosure and cable layout are designed around the parts above.

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

The Wi-Fi saved by Raspberry Pi Imager remains the preferred connection. If
neither saved Wi-Fi nor Ethernet connects for 30 seconds, join the protected
**TrainUI** hotspot with password **TRAINUI1**, then open `http://10.42.0.1`
and enter the replacement Wi-Fi name and password. While this hotspot is
active, the bottom System Health panel shows its name, password, and setup-page
address. During a normal Wi-Fi connection, that panel never displays the
network password.

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

Check the automatic Wi-Fi setup service:

```bash
systemctl status trainui-wifi-setup.service
sudo journalctl -u trainui-wifi-setup.service --since today
```

## Troubleshooting

| Problem | What to check |
| --- | --- |
| SSH does not connect | Make sure SSH was enabled and try the Pi's IP address. |
| Nothing opens after reboot | Make sure Raspberry Pi OS reaches the desktop, then check the log above. |
| Arrivals are unavailable | Check the internet connection. Some trains do not run at every station all day. |
| Wi-Fi keeps disconnecting | Make sure the original Pi Zero W is using a 2.4 GHz network. After 30 seconds offline, join **TrainUI** with password **TRAINUI1** and open `http://10.42.0.1`. |
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
├── Assembly Guide/     # Step-by-step build guide and local parts photos
├── image/             # Raspberry Pi image build files
├── installer/         # One-command installer and route setup
├── tests/             # Catalog, display, and installer checks
├── requirements.txt
├── timertest.py       # Main Train UI XL program
└── README.md
```
