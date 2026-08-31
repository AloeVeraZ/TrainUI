<div align="center">

# Train UI XL

### My full-size NYC train display

[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi_OS-c51a4a?style=flat-square&logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/software/)
[![Code](https://img.shields.io/badge/Code-Python-3776ab?style=flat-square&logo=python&logoColor=white)](timertest.py)
[![Data](https://img.shields.io/badge/Data-MTA_Realtime-2563eb?style=flat-square)](https://www.mta.info/developers)

<img src="../assets/images/train-ui-xl.jpg" width="420" alt="Train UI XL showing live departures">

[Parts](#parts) • [CAD](#cad-files) • [Assembly](Assembly%20Guide/) • [Install](#install) • [Commands](#commands)

</div>

---

## Overview

I built Train UI XL around a Raspberry Pi Zero W and a 10.1-inch screen. It shows arrivals, service alerts, weather, time, and Pi health, then starts itself whenever the Pi boots.

> [!WARNING]
> This build needs soldering. Keep power disconnected. Feed the cut Micro-USB cable through the printed back **before soldering**, verify polarity with a multimeter, solder red to `V` and black to `G`, insulate every unused wire, and check for a `V`–`G` short before power-up.

## Parts

This is the bill of materials for the XL build.

| Qty. | Core part |
| ---: | --- |
| 1 | Original Raspberry Pi Zero W |
| 1 | 10.1-inch 1024 × 600 HDMI display |
| 1 | MicroSD card |
| 1 | Stable 5V power supply |

### Cables and hardware

<table>
  <tr>
    <td width="33%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0G5YZJLVZ"><img src="Assembly%20Guide/images/parts/usb-c-to-micro-usb-adapter.jpg" width="240" alt="USB-C female to Micro-USB male adapter cable"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0G5YZJLVZ">USB-C to Micro-USB adapter lead</a></strong><br>
      Becomes the internal Pi power lead.
    </td>
    <td width="33%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0CNGV7FQJ"><img src="Assembly%20Guide/images/parts/angled-mini-hdmi-cable.jpg" width="240" alt="Angled HDMI to mini-HDMI cable"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0CNGV7FQJ">90-degree HDMI to mini-HDMI cable</a></strong><br>
      Connects the Pi to the screen.
    </td>
    <td width="33%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0D5V3TZLB"><img src="Assembly%20Guide/images/parts/heat-set-inserts.jpg" width="240" alt="M2 through M5 heat-set insert kit"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0D5V3TZLB">M2–M5 heat-set inserts</a></strong><br>
      Adds metal threads to the printed parts.
    </td>
  </tr>
  <tr>
    <td width="33%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0F3WVBGCP"><img src="Assembly%20Guide/images/parts/usb-c-panel-mount.jpg" width="240" alt="USB-C female panel-mount socket boards"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0F3WVBGCP">USB-C panel-mount socket</a></strong><br>
      Becomes the outside power inlet.
    </td>
    <td width="33%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0F87W7P59"><img src="Assembly%20Guide/images/parts/micro-usb-cable.jpg" width="240" alt="Short 90-degree Micro-USB male-to-male cable"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0F87W7P59">Short 90-degree Micro-USB cable</a></strong><br>
      Keeps the internal power run compact.
    </td>
    <td width="33%" valign="top" align="center">
      <a href="https://www.amazon.com/dp/B0FF4TDYKZ"><img src="Assembly%20Guide/images/parts/countersunk-fasteners.jpg" width="240" alt="Countersunk M2, M2.5, and M3 fastener assortment"></a><br>
      <strong><a href="https://www.amazon.com/dp/B0FF4TDYKZ">Countersunk fasteners</a></strong><br>
      Holds low-profile parts flush.
    </td>
  </tr>
  <tr>
    <td colspan="3" align="center">
      <table width="67%">
        <tr>
          <td width="50%" valign="top" align="center">
            <a href="https://www.amazon.com/dp/B0FGJ9FRGQ"><img src="Assembly%20Guide/images/parts/m3-fasteners.jpg" width="240" alt="M3 socket-head screw, nut, and washer assortment"></a><br>
            <strong><a href="https://www.amazon.com/dp/B0FGJ9FRGQ">M3 socket-head fasteners</a></strong><br>
            Use four M3 × 25 mm screws to close the case.
          </td>
          <td width="50%" valign="top" align="center">
            <a href="https://www.amazon.com/dp/B07ZH9GJWP"><img src="Assembly%20Guide/images/parts/self-tapping-screws.jpg" width="240" alt="Small black self-tapping screw assortment"></a><br>
            <strong><a href="https://www.amazon.com/dp/B07ZH9GJWP">Small self-tapping screws</a></strong><br>
            Secures light internal parts.
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>

**Tools:** soldering iron, wire cutters, wire strippers, multimeter, heat-shrink, heat-set tip, and matching hand tools.

## CAD files

| File | Use |
| --- | --- |
| [case for screen.step](CAD/case%20for%20screen.step) | Complete STEP assembly |
| [Only 3DP files.step](CAD/Only%203DP%20files.step) | **3D-printed parts only** |
| [case for screen.f3z](CAD/case%20for%20screen.f3z) | Editable Fusion 360 archive |

If you only want to slice or print the enclosure, download **Only 3DP files.step**. The full STEP and Fusion archive also include reference assembly content.

## Assembly

The [step-by-step assembly guide](Assembly%20Guide/) covers the faceplate, screen, Pi, power inlet, wiring, and final enclosure.

## Install

1. Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to install Raspberry Pi OS 32-bit with Desktop.
2. Add 2.4 GHz Wi-Fi, enable SSH, and create your user.
3. Connect the screen, SSH into the Pi, and run:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/installer/install.sh | bash
```

Choose a train and station. The installer sets the 270-degree display, automatic startup, and Wi-Fi recovery, then reboots.

If the Pi stays offline for 30 seconds, join **TrainUI** with password **TRAINUI1** and open `http://10.42.0.1`. The screen shows these setup details only while the hotspot is active.

## Update or change stations

Run the same command again:

```bash
curl -fsSL https://raw.githubusercontent.com/AloeVeraZ/TrainUI/main/Train%20UI%20XL/installer/install.sh | bash
```

## Commands

```bash
# View the log
tail -f "$HOME/TrainUI/Train UI XL/trainui.log"

# Check Wi-Fi setup
systemctl status trainui-wifi-setup.service
sudo journalctl -u trainui-wifi-setup.service --since today
```

## Quick fixes

| Problem | Check |
| --- | --- |
| SSH fails | Try the Pi's IP address and confirm SSH is enabled. |
| Screen stays blank | Let Raspberry Pi OS reach the desktop, then check the log. |
| Wi-Fi fails | Use 2.4 GHz, or join the setup hotspot after 30 seconds. |
| Rotation is wrong | Mount the screen at 270 degrees and rerun the installer. |

## Development

```bash
python3 -m unittest discover -s tests -v
python3 tests/validate_live_feeds.py
python3 timertest.py --smoke-test
```
