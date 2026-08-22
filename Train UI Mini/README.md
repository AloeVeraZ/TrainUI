# Train UI Mini

Train UI Mini is a one-page, always-on NYC subway and Staten Island Railway departure board for the **Elecrow CrowPanel ESP32-S3 2.13-inch 122×250 black-and-white e-paper display**.

It is a compact e-paper adaptation of [AloeVeraZ/TrainUI](https://github.com/AloeVeraZ/TrainUI). It preserves TrainUI's glanceable hierarchy—station identity, both travel directions, three arrivals per direction, service status, NYC weather, time, and connection state—while translating the original color UI to monochrome cards sized for this display.

## Features

- One screen only; no page navigation is required
- Live MTA GTFS-Realtime arrivals with no API key
- Next three arrivals for both directions
- Route- and station-specific MTA service alert headline
- NYC weather from Open-Meteo
- Always-visible `ONLINE` or `OFFLINE` state
- Complete route and station selector derived from TrainUI's bundled MTA catalog
- All numbered and lettered NYC subway services, three shuttles, and Staten Island Railway
- Phone-friendly setup webpage hosted directly by the ESP32
- Offline sample arrivals for testing without internet
- Fast e-paper updates with a periodic full refresh to limit ghosting
- No server, account, phone app, antenna, or additional hardware

## First-time setup

After the first upload, the display shows setup instructions:

1. Join Wi-Fi **TrainUIMini** from a phone or computer.
2. Enter password **TRAINUI1**.
3. Open **http://192.168.4.1**.
4. Enter home Wi-Fi.
5. Choose a train.
6. Choose a station served by that train.
7. Save. The board restarts into its one-page departure display.

The train and station are intentionally not preselected. Press the physical **Menu** button to reopen setup and change either choice later.

## Controls

| Control | Action |
|---|---|
| Menu | Open Wi-Fi/train/station setup for 15 minutes |
| Dial press | Toggle live mode and clearly marked offline sample mode |
| Back | Force an immediate live refresh |
| Dial up/down | Unused because the project has one page |

## Arduino IDE

1. Install **esp32 by Espressif Systems**. Elecrow's reference firmware was tested with version **2.0.10**.
2. Open `TrainUIMiniCode/TrainUIMiniCode.ino`.
3. Select **ESP32S3 Dev Module**.
4. Set **Flash Size** to **8MB (64Mb)**.
5. Set **PSRAM** to **OPI PSRAM**.
6. Set **USB CDC On Boot** to **Enabled**.
7. Select the USB port and upload.

The 8 MB PSRAM setting is required because the ESP32 downloads and parses MTA protobuf feeds locally.

## PlatformIO

Open the `TrainUIMiniCode` folder in VS Code and run **PlatformIO: Upload**. Its included `platformio.ini` contains the ESP32-S3, flash, PSRAM, and USB configuration.

## Easy Wi-Fi defaults

Wi-Fi is normally entered through setup. It can alternatively be placed in `TrainUIMiniCode/UserConfig.h`:

```cpp
constexpr char WIFI_SSID[] = "your-wifi";
constexpr char WIFI_PASSWORD[] = "your-password";
```

A train and station must still be chosen once through the setup page.

## Data and privacy

- Arrivals refresh every 60 seconds from the selected public MTA GTFS-Realtime feed.
- Alerts refresh every five minutes from the public MTA alert feed.
- Weather refreshes every ten minutes through Open-Meteo.
- Time is synchronized through NTP and uses New York daylight-saving rules.
- Credentials and the chosen route/station remain in ESP32 Preferences flash.
- No analytics, custom backend, API key, or account is used.
- HTTPS certificate verification is disabled to keep the standalone firmware small. Public endpoints receive no secret, but a hostile network could alter displayed public data.

Arrival and alert information is informational. Always follow official MTA announcements and signage.

## Project structure

```text
TrainUIMiniCode/
  TrainUIMiniCode.ino   Arduino IDE sketch entry point
  TrainUIMiniMain.cpp   Setup portal, one-page UI, settings, and scheduler
  SubwayCatalog.h       Embedded TrainUI route/station catalog
  MtaClient.cpp/.h      Direct GTFS-Realtime protobuf downloader/parser
  MiniWeather.cpp/.h    Compact Open-Meteo client
  EpaperDisplay.cpp/.h  SSD1680 e-paper driver and graphics
  BoardPins.h           CrowPanel pin mapping
  UserConfig.h          Optional IDE Wi-Fi defaults
  platformio.ini        Reproducible ESP32-S3 build configuration
README.md
LICENSE
```

## Credits

Designed and built by **aloe**. Train UI Mini is based on the interface and configuration model of [TrainUI](https://github.com/AloeVeraZ/TrainUI). MTA route/station data remains subject to its source terms.

## License

MIT

