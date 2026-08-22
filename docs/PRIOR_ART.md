# Prior Art: CtPU / CCtPU Terminology

## Origin

The terms **CtPU** (Conversion to Physical Units) and **CCtPU** (Calibrated CtPU) 
were independently coined in August 2026 as part of the CtPU-multi-curveXY research 
preview for software-defined instrumentation on FX2-based oscilloscopes.

## First Public Use

- **Date**: August 9, 2026
- **Location**: github.com/dtba3a-del/OpenHantek6022/tree/CtPU-multi-curveXY
- **Context**: Pre-release research preview of universal measurement frontend
- **Domain**: Software-defined instrumentation, metrological conversion for ADC data

## Distinction from Other Uses

CtPU/CCtPU in this context refers specifically to:
- Linear conversion of ADC counts to SI units (k·x + b)
- Two-point calibration against physical reference standards
- Multi-channel mathematical operations with independent unit conversions

This is distinct from:
- Tensor Processing Units (machine learning accelerators)
- Current Transformer Protection Units (electrical protection)
- Crank Trigger Pick-Up sensors (automotive)

## Author

Independent researcher, dtba3a-del
