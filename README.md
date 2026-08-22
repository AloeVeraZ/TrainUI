<div align="center">

# Train UI

### Two ways to build an always-on NYC train board

Live arrivals · Service alerts · Weather · A screen made to be glanced at

[Full Train UI](Train%20UI/) · [Train UI Mini](Train%20UI%20Mini/)

</div>

---

Train UI started with a simple idea: the useful part of checking a transit app should already be sitting on the desk. No unlocking a phone, opening an app, choosing a station, or getting distracted along the way. You look over and see when the next trains are coming.

This repository contains two versions of that idea. **Train UI** is the original Raspberry Pi build with a large color display and a more detailed interface. **Train UI Mini** puts the same basic information on a small e-paper screen that already has an ESP32 built into it.

They are not meant to replace each other. The full version is the better display; the Mini is the easier project to actually build.

## The two versions

| | Train UI | Train UI Mini |
|---|---|---|
| Display | 10.1-inch 1024×600 color HDMI LCD | 2.13-inch 122×250 black-and-white e-paper |
| Computer | Raspberry Pi Zero W | ESP32-S3 built into the display |
| Software | Raspberry Pi OS and Python | Arduino firmware |
| Interface | Full dashboard with larger panels and system information | One compact page with the important information |
| Installation | Raspberry Pi Imager, SSH, then the installer script | Open the sketch in Arduino IDE and upload it |
| Physical build | Pi, display, cables, storage, power, and a three-part printed enclosure | One CrowPanel board, a USB cable, and a printed case |
| Best for | A larger permanent departure board | A small desk display and a first hardware project |

Both versions let you choose the train and station you care about. Both use public MTA realtime data, show arrivals in both directions, and are designed to stay on instead of behaving like another app.

## Train UI

[Train UI](Train%20UI/) is the original build. It runs on an original Raspberry Pi Zero W connected to a 10.1-inch HDMI display. The extra screen space is used for a full departure-board layout: arrivals in both directions, service information, weather, date and time, and Raspberry Pi health details.

It is the version to build when the display itself is the main object. It is larger, easier to read from across a room, has color route badges, and can show more information without squeezing anything together.

The tradeoff is setup. A Raspberry Pi is a small Linux computer, so the build involves flashing Raspberry Pi OS, configuring Wi-Fi and SSH, connecting the Pi to the display, and running the included installer script. The installer handles the Python environment, train and station selection, automatic startup, screen rotation, and the settings needed to keep the display awake.

### Why choose the full version?

- The 10.1-inch color screen is much easier to read at a distance.
- It has room for the complete Train UI layout and system-health information.
- The Raspberry Pi gives the project more flexibility for future additions.
- The HDMI display and Pi can be serviced or upgraded separately.

### What makes it harder?

- It requires more individual hardware and cables.
- You need to set up Raspberry Pi OS and connect through SSH.
- The enclosure is larger and has more parts to fit together.
- A normal LCD uses more power than a small e-paper panel.

The complete hardware list, Raspberry Pi preparation, installer instructions, CAD status, and troubleshooting notes are in the [Train UI README](Train%20UI/README.md).

## Train UI Mini

[Train UI Mini](Train%20UI%20Mini/) exists to lower the barrier to entry. It uses the [Elecrow CrowPanel ESP32-S3 2.13-inch e-paper display](https://www.amazon.com/dp/B0H25DMJ8M), which already combines the screen, ESP32, Wi-Fi, buttons, and controls on one board.

That changes the whole build. There is no separate Raspberry Pi, microSD card, HDMI screen, operating system, or Linux setup to learn. You can order the display, 3D print the case, connect it over USB, and upload the included Arduino sketch. On first boot, the board creates its own setup page where you enter Wi-Fi and choose a train and station.

The Mini keeps the display to one page. It shows the selected station, three arrivals for each direction, service status, weather, time, and a clear online or offline indicator. E-paper updates slowly by nature, but that works well here: subway information changes in minutes, not sixty times per second, and the screen is meant to sit quietly on a desk.

### Why choose the Mini?

- The controller and display arrive as one board.
- Arduino IDE is the only software needed to upload it.
- It costs less to get started and requires fewer parts.
- The enclosure is smaller and simpler to print.
- It is a much friendlier first step into electronics than a full Raspberry Pi setup.
- E-paper uses very little power between refreshes and remains readable in bright light.

### What do you give up?

- The screen is much smaller and only black and white.
- E-paper cannot update as smoothly or frequently as an LCD.
- The one-page layout has less room for detail.
- The ESP32 has less memory and processing headroom than a Raspberry Pi.
- It is meant to be a focused departure board, not a general-purpose computer.

The exact Arduino board settings, first-boot Wi-Fi steps, offline test mode, controls, and source layout are in the [Train UI Mini README](Train%20UI%20Mini/README.md).

## Which one should I build?

Build **Train UI** if you want the full-size version and do not mind spending some time setting up a Raspberry Pi. It is the better choice for a wall, shelf, or anywhere the display needs to be readable from farther away.

Build **Train UI Mini** if you want the simplest path from buying parts to having a working train display on your desk. It was made specifically for people who like the idea of Train UI but do not want the price, hardware, or Linux learning curve of the full build.

## Repository layout

```text
TrainUI/
├── Train UI/        # Original Raspberry Pi version, installer, tests, and CAD
└── Train UI Mini/   # ESP32-S3 e-paper version and Arduino firmware
```

Each folder is self-contained and has its own README. Start with the folder for the hardware you want to build.

---

<div align="center">

Designed and built by **aloe**.

</div>
