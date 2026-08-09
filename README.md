# CtPU-multi-curveXY
### Universal Measurement Frontend · Research Preview

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Qt5](https://img.shields.io/badge/Qt-5.5+-green.svg)](https://www.qt.io)
[![fx2adc](https://img.shields.io/badge/Firmware-fx2adc-orange.svg)](https://github.com/steve-m/fx2adc)

&gt; **Research Preview.** CtPU-multi-curveXY is an experimental branch exploring the frontier of software-defined instrumentation. Capabilities evolve based on community signal and hardware feedback. Not recommended for safety-critical or certified metrology workflows without independent validation.

---

## Frontier Capabilities

| Module | Status | Description |
|--------|--------|-------------|
| **CtPU** | Stable | Channel-to-Physical-Unit conversion. Any sensor with analog output → SI units via `k·x+b`. No sketches. No IDE. |
| **CCtPU** | Stable | Two-point calibration (Zero / Span) against a physical reference standard. Datasheet-optional metrology. |
| **multi-curveXY** | Stable | 4 concurrent curves (2 real + 2 math) with arbitrary real/math cascades. V, A, P, R — simultaneously. |
| **XY Recorder** | Stable | Continuous chart-recorder acquisition. Anti-aliased cascade decimation. Pure XY CSV export. Tape & Sheet modes. |
| **fx2adc** | Stable | Alternative FX2 firmware for ISDS205 and compatible scopes. 30 MSPS, improved stability over stock Hantek firmware. |
| **RCL Broadband** | In Development | Wideband impedance analysis via swept excitation. |
| **I/Q Decode** | Concept | R820T tuner integration. 42–1002 MHz downconversion + undersampling I/Q demodulation via fx2adc. |
| **3D Waterfall** | Concept | Z-axis temporal stacking for channel separation. Hardware-accelerated depth visualization. |

---

## What This Enables

**Without IDE. Without sketches. With or without datasheets.**

Connect a sensor. Apply a physical reference. Read SI units directly.

- LM335 → °C / K (CtPU, formula from datasheet)
- Strain gauge → kg / N (CCtPU, calibrated against standard weights)
- Current shunt → A → P = V·A, R = V/A (multi-curveXY, limit 4 curves)
- R820T + fx2adc → SDR analyzer 42–1002 MHz (I/Q decode, concept)

XY Recorder captures long-duration transients: battery charge cycles, thermal profiles, mechanical hysteresis — streamed to disk as pure XY CSV.

---

## Quick Start

```bash
# Qt5 build
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH=/path/to/Qt5
make -j$(nproc)
```

**Windows:** binaries include Zadig 2.9 for WinUSB/libusb driver setup.  
**fx2adc:** firmware auto-loads to RAM via OpenHantek GUI on device connect.

---

## Research Preview Notice

This branch is an **evaluation target**, not a production-certified instrument. Features iterate based on:

- Hardware feedback from ISDS205 / FX2 deployments
- Community signal on XY recorder and multi-curve workflows
- Integration tests with fx2adc and third-party tuners

Behavior may shift between releases as the architecture converges. For reproducible measurement campaigns, pin to a tagged release and document the commit hash.

---

## Accelerate the Frontier

Iteration velocity depends on hardware access, metrological validation time, and the density of community signal. If this trajectory intersects with your instrumentation needs, participation is welcome — see `.github/FUNDING.yml` for requisites.

This is not a pre-order, a feature purchase, or a service contract. It is opt-in participation in a research preview. Priority and co-design access are granted at the maintainer's discretion based on alignment with the research trajectory.

---

*CtPU-multi-curveXY is maintained independently of upstream OpenHantek6022. This branch focuses on software-defined instrumentation, metrological frontends, and RF integration — distinct from the oscilloscope-centric scope of the original project.*
