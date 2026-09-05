# Train UI XL Trackside

Train UI XL Trackside is a dedicated, easy-to-read version commissioned for a
bar. It keeps the same Raspberry Pi Zero W hardware, MTA live departures,
Wi-Fi recovery, scheduled display power, automatic startup, and installation
flow as [Train UI XL](../README.md). It lives in its own folder so the
Trackside layout can be maintained separately from the main display.

## What is different

- The clock and date are enlarged for viewing across a room, with responsive
  sizing so the full weekday and month remain readable.
- Departure numbers and their `MIN` labels are enlarged to the largest size
  that fits each portrait card without clipping.
- The service-change panel is replaced by a five-day weather forecast.
- System health is compact and stays at the bottom with only CPU temperature,
  uptime, IP address, and Wi-Fi connection.

The Trackside installer uses separate application, configuration, log, Wi-Fi,
schedule, and systemd names so it does not overwrite a regular Train UI XL
installation. Its setup hotspot is **TrainUI Trackside** with password
**TRAINUI1** at `http://10.42.0.1`.

## Install

Use Raspberry Pi OS 32-bit with Desktop, enable SSH, add the 2.4 GHz network in
Raspberry Pi Imager, and run this as the normal Pi user:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/Train%20UI%20XL%20Trackside/installer/install.sh | bash
```

Choose the train and station, then answer `Y` or `N` for daily display sleep.
Enter times as exactly four digits in 24-hour `HHMM` format: `2300` is 11:00
PM, `0800` is 8:00 AM, and `2400` is midnight.

## Commands

```bash
# Update Trackside, change the station, or review the sleep schedule
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/Train%20UI%20XL%20Trackside/installer/install.sh | bash

# Change only the Trackside display schedule
trainui-trackside-schedule

# View the Trackside log
tail -f "$HOME/TrainUI-Trackside/Train UI XL/Train UI XL Trackside/trainui-trackside.log"
```

Scheduled sleep powers down only the display. The logged-in desktop and
Trackside app remain active, so wake time returns directly to the dashboard.

## Hardware and assembly

Use the shared [parts and CAD files](../README.md) and the
[step-by-step assembly guide](../Assembly%20Guide/). The enclosure, screen,
Raspberry Pi Zero W orientation, power wiring, and fasteners are unchanged.
