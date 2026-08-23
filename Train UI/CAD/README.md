<div align="center">

# TrainUI Enclosure CAD

### Printable and editable enclosure CAD for the Raspberry Pi Zero W transit board

[![Status](https://img.shields.io/badge/Status-In_Development-f57c00?style=flat-square)](#development-status)
[![Platform](https://img.shields.io/badge/Hardware-Pi_Zero_W-c51a4a?style=flat-square)](https://www.raspberrypi.com/)
[![Display](https://img.shields.io/badge/Display-10.1%22_HDMI-0078d4?style=flat-square)](https://www.amazon.com/dp/B0FMF3RTPC)
[![Parent](https://img.shields.io/badge/Project-TrainUI-0039a6?style=flat-square)](../)

This folder is reserved for the 3D-printed enclosure models, printable exports, hardware notes, and assembly guidance for the TrainUI project.

<strong>Quick navigation:</strong><br>
[Hardware Overview](#hardware-overview) | [Enclosure Design](#enclosure-design) | [Development Status](#development-status) | [Back to TrainUI](../)

</div>

---

## Hardware Overview

The enclosure is being made around the exact Pi Zero W and 10.1-inch display used by the main TrainUI build.

| Component | Specification | Details |
| --- | --- | --- |
| Main controller | Raspberry Pi Zero W | Compact, low-power single-board computer running Raspberry Pi OS (32-bit) |
| Display | HAMTYSAN 10.1-inch IPS LCD | 1024×600 resolution, 16:9 aspect ratio, HDMI input ([Amazon ASIN B0FMF3RTPC](https://www.amazon.com/dp/B0FMF3RTPC)) |
| Assembly method | Heat-set inserts and fasteners | Threaded brass inserts and machine screws through matched assembly holes |
| Manufacturing | 3D-printed FDM parts | Three-piece modular enclosure design |

## Enclosure Design

The physical case is designed as three interlocking 3D-printed components:

1. **Front Bezel:** Frames the 10.1-inch LCD panel and secures the display without blocking active viewing area.
2. **Main Housing:** Encloses the Raspberry Pi Zero W, power distribution, and internal HDMI/power routing.
3. **Rear Service Cover:** Provides ventilated access to the Pi Zero W, microSD card, and mounting points.

> [!NOTE]
> Heat-set threaded inserts are used throughout rather than self-tapping screws or permanent snap fits, allowing the enclosure to be repeatedly opened and serviced during development.

## Development Status

The CAD models are currently undergoing dimensional validation and fit checks against the physical HAMTYSAN panel and cable clearances. Source files (`.step`, `.f3d`) and printable `.stl`/`.3mf` packages will be added here once the design is finalized.

---

<div align="center">

Designed and documented for the **[TrainUI](../)** project.

</div>
