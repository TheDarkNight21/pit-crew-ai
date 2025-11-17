# OpenF1 Telemetry Data Guide

## Overview

This project now supports comprehensive telemetry data loading from the OpenF1 API, including car data, weather, race events, and more.

---

## 📊 Data Availability Matrix

### ✅ AVAILABLE from OpenF1 API

#### Car State Fields
| Field | Source Endpoint | Frequency | Description |
|-------|----------------|-----------|-------------|
| `speed` | `car_data` | ~3.7 Hz | Vehicle speed (km/h) |
| `throttle` | `car_data` | ~3.7 Hz | Throttle percentage (0-100) |
| `brake` | `car_data` | ~3.7 Hz | Brake status (0 or 1) |
| `rpm` | `car_data` | ~3.7 Hz | Engine RPM |
| `n_gear` | `car_data` | ~3.7 Hz | Current gear (1-8) |
| `drs` | `car_data` | ~3.7 Hz | DRS status (0-14, various states) |
| `gap_to_leader` | `intervals` | ~4 seconds | Gap to race leader (seconds) |
| `gap_to_car_ahead` | `intervals` | ~4 seconds | Gap to car ahead (seconds) |
| `gap_to_car_behind` | `intervals` (derived) | ~4 seconds | Gap to car behind (calculated) |

#### Track State Fields
| Field | Source Endpoint | Frequency | Description |
|-------|----------------|-----------|-------------|
| `track_temperature` | `weather` | ~1 minute | Track surface temperature (°C) |
| `air_temperature` | `weather` | ~1 minute | Ambient air temperature (°C) |
| `rainfall` | `weather` | ~1 minute | Rainfall (0 or 1) |
| `humidity` | `weather` | ~1 minute | Relative humidity (%) |
| `pressure` | `weather` | ~1 minute | Atmospheric pressure (mbar) |
| `wind_speed` | `weather` | ~1 minute | Wind speed (m/s) |
| `wind_direction` | `weather` | ~1 minute | Wind direction (degrees) |
| `track_status` | `race_control` (derived) | Event-based | green, yellow, vsc, safety_car |

#### Position & Lap Fields
| Field | Source Endpoint | Frequency | Description |
|-------|----------------|-----------|-------------|
| `position` | `laps` or `position` | Per lap or higher | Track position (1-20) |
| `lap_number` | `laps` | Per lap | Current lap number |
| `lap_duration` | `laps` | Per lap | Lap time in seconds |
| `is_pit_out_lap` | `laps` | Per lap | Boolean flag |
| `x, y, z` | `location` | ~3.7 Hz | 3D track coordinates |

#### Tire Information
| Field | Source Endpoint | Frequency | Description |
|-------|----------------|-----------|-------------|
| `compound` | `stints` | Per stint | SOFT, MEDIUM, HARD, INTERMEDIATE, WET |
| `tyre_age_at_start` | `stints` | Per stint | Tire age in laps |

#### Derived Fields
| Field | Calculation | Description |
|-------|------------|-------------|
| `delta_vs_best_lap` | Per-driver lap analysis | Time delta from driver's best lap |
| `gap_to_car_behind` | From intervals data | Calculated from position order |

#### Event Types
| Event Type | Source | Description |
|------------|--------|-------------|
| `lap` | `laps` | Lap completion event |
| `pit_in` | `pit` | Car entering pit lane |
| `pit_out` | `pit` | Car exiting pit lane |
| `yellow_flag` | `race_control` | Yellow flag incident |
| `green_flag` | `race_control` | Track cleared |
| `red_flag` | `race_control` | Session stopped |
| `vsc` | `race_control` | Virtual safety car deployed |
| `vsc_end` | `race_control` | Virtual safety car ending |
| `safety_car` | `race_control` | Safety car deployed |
| `safety_car_end` | `race_control` | Safety car ending |
| `rain_start` | `race_control` | Rain detected |
| `rain_end` | `race_control` | Rain stopped |
| `race_control` | `race_control` | Other race control messages |

---

### ❌ NOT AVAILABLE from OpenF1

These fields were requested but are **not available** through the OpenF1 API:

#### Car State - Not Available
- `tire_wear` (%) - No wear percentage data available
- `fuel_load` (kg) - Not provided by FIA/FOM
- `engine_mode` - Not publicly available
- `ers_charge` (%) - Not publicly available
- `battery_deploy_mode` - Not publicly available

#### Track State - Not Available
- `weather_rain_probability` - Only actual rainfall is available

#### Strategy Fields - Require Custom Implementation
- `predicted_pit_window_start` - Must be calculated with ML/heuristics
- `predicted_pit_window_end` - Must be calculated with ML/heuristics

> **Note:** The missing fields would require either:
> 1. Data from FIA timing system (not publicly available)
> 2. Custom ML models to predict/estimate values
> 3. Third-party data sources

---

## 🚀 Quick Start

### 1. Basic Usage

```python
from app.data_loader import (
    fetch_drivers, fetch_laps, fetch_car_data,
    fetch_intervals, fetch_weather, fetch_race_control,
    fetch_stints, fetch_pit_stop, fetch_position
)
from app.process_data import create_telemetry_race_data

# Fetch all data for a session
session_key = 9472  # Example session key

drivers_df = fetch_drivers(session_key)
laps_df = fetch_laps(session_key)
car_data_df = fetch_car_data(session_key)
intervals_df = fetch_intervals(session_key)
weather_df = fetch_weather(session_key)
race_control_df = fetch_race_control(session_key)
stints_df = fetch_stints(session_key)
pit_stops_df = fetch_pit_stop(session_key)
position_df = fetch_position(session_key)

# Create comprehensive telemetry CSV
telemetry_df = create_telemetry_race_data(
    laps_df=laps_df,
    drivers_df=drivers_df,
    car_data_df=car_data_df,
    intervals_df=intervals_df,
    weather_df=weather_df,
    race_control_df=race_control_df,
    position_df=position_df,
    stints_df=stints_df,
    pit_stops_df=pit_stops_df,
    output_path="race_telemetry.csv"
)
```

### 2. Run Example Script

```bash
python example_telemetry.py
```

This will fetch Monaco 2025 Race data and create a comprehensive CSV.

---

## 📁 Output CSV Structure

The generated CSV contains chronologically ordered events with the following structure:

### Core Columns (Always Present)
- `event_id` - Sequential event identifier
- `timestamp` - ISO format timestamp
- `event_type` - Type of event (lap, pit_in, pit_out, etc.)
- `driver_number` - Driver identifier
- `driver_name` - Driver acronym (VER, HAM, etc.)
- `team_name` - Team name
- `team_colour` - Team color hex code

### Lap-Based Columns
- `lap_number` - Current lap
- `lap_duration` - Lap time in seconds
- `is_pit_out_lap` - Boolean
- `position` - Track position
- `delta_vs_best_lap` - Time delta from best lap

### Telemetry Columns (if car_data provided)
- `speed` - km/h
- `throttle` - 0-100%
- `brake` - 0 or 1
- `rpm` - Engine RPM
- `n_gear` - Gear number
- `drs` - DRS status

### Gap/Interval Columns (if intervals provided)
- `gap_to_leader` - Seconds
- `gap_to_car_ahead` - Seconds
- `gap_to_car_behind` - Seconds (calculated)

### Weather Columns (if weather provided)
- `air_temperature` - °C
- `track_temperature` - °C
- `rainfall` - Boolean
- `humidity` - %
- `pressure` - mbar
- `wind_speed` - m/s
- `wind_direction` - Degrees

### Tire Columns (if stints provided)
- `compound` - Tire type
- `tyre_age_at_start` - Laps

### Event-Specific Columns
- `pit_duration` - For pit_in/pit_out events
- `message` - For race_control events
- `flag` - For flag events
- `track_status` - Derived track condition

---

## 🔧 New API Functions

### Added to `app/data_loader.py`

```python
fetch_car_data(session_key, driver_number=None)
# Returns: speed, throttle, brake, rpm, n_gear, drs

fetch_intervals(session_key)
# Returns: gap_to_leader, interval (gap to car ahead)

fetch_weather(session_key)
# Returns: air_temp, track_temp, rainfall, humidity, pressure, wind

fetch_race_control(session_key)
# Returns: flags, safety cars, penalties, messages

fetch_position(session_key)
# Returns: position changes with high granularity

fetch_location(session_key, driver_number=None)
# Returns: x, y, z coordinates on track
```

### Added to `app/process_data.py`

```python
create_telemetry_race_data(...)
# Comprehensive function that merges all data sources
# Creates event-based telemetry CSV with proper time alignment
```

---

## 💡 Use Cases

### 1. Machine Learning Training
```python
import pandas as pd

df = pd.read_csv("race_telemetry.csv")

# Filter to lap events only
lap_data = df[df['event_type'] == 'lap']

# Features for pit stop prediction
features = lap_data[[
    'lap_number', 'lap_duration', 'tyre_age_at_start',
    'compound', 'track_temperature', 'gap_to_leader'
]]
```

### 2. Race Replay/Simulation
```python
# Events are chronologically sorted
for idx, event in df.iterrows():
    if event['event_type'] == 'pit_in':
        print(f"Lap {event['lap_number']}: {event['driver_name']} pits")
    elif event['event_type'] == 'lap':
        print(f"{event['driver_name']} completes lap {event['lap_number']} "
              f"in {event['lap_duration']:.3f}s - P{event['position']}")
```

### 3. Strategy Analysis
```python
# Analyze tire degradation
stints = df[df['compound'].notna()].groupby(['driver_name', 'compound']).agg({
    'lap_duration': ['mean', 'std'],
    'lap_number': 'count'
})
```

---

## ⚠️ Important Notes

### Data Frequency Considerations

Different endpoints have different update frequencies:
- **Car data**: ~3.7 Hz (very high frequency, large dataset)
- **Intervals**: ~4 seconds (race sessions only)
- **Weather**: ~1 minute
- **Laps**: Once per lap completion

The `create_telemetry_race_data()` function uses time-based merging (`pd.merge_asof`) to align these different frequencies.

### Large Datasets

Full race car_data can be **very large** (100k+ rows for a single race). Consider:
- Fetching for specific drivers only: `fetch_car_data(session_key, driver_number=1)`
- Processing in chunks
- Using only necessary endpoints

### Race Sessions Only

The `intervals` endpoint only works for race sessions, not practice or qualifying.

---

## 🛠️ Extending the System

### Adding Custom Derived Fields

You can extend `create_telemetry_race_data()` to add custom calculations:

```python
# Example: Add fuel usage estimation (fictional)
all_events['estimated_fuel_used'] = all_events.groupby('driver_number')['lap_number'].transform(
    lambda x: x * 2.0  # ~2kg per lap estimate
)

# Example: Tire wear estimation based on compound and age
def estimate_tire_wear(row):
    if pd.isna(row['tyre_age_at_start']):
        return None
    base_wear = row['tyre_age_at_start'] * 1.5
    if row['compound'] == 'SOFT':
        return min(base_wear * 1.3, 100)
    elif row['compound'] == 'MEDIUM':
        return min(base_wear * 1.0, 100)
    else:  # HARD
        return min(base_wear * 0.8, 100)

all_events['estimated_tire_wear'] = all_events.apply(estimate_tire_wear, axis=1)
```

---

## 📚 OpenF1 API Documentation

Full API documentation: https://openf1.org

### All Available Endpoints

1. `car_data` - Vehicle telemetry
2. `drivers` - Driver information
3. `intervals` - Gap data
4. `laps` - Lap timing
5. `location` - Track coordinates
6. `meetings` - Grand Prix events
7. `pit` - Pit stops
8. `position` - Position changes
9. `race_control` - Race incidents/flags
10. `sessions` - Session metadata
11. `stints` - Tire stints
12. `weather` - Weather conditions

---

## 🎯 Summary

**Available for Free:**
- ✅ Full car telemetry (speed, throttle, brake, rpm, gear, DRS)
- ✅ Gap/interval data
- ✅ Weather and track conditions
- ✅ Race control events (flags, safety cars)
- ✅ Pit stop data with timing
- ✅ Tire compound and age
- ✅ Position and location data

**Not Available:**
- ❌ Tire wear percentage
- ❌ Fuel load
- ❌ ERS/battery data
- ❌ Engine modes

**Requires Custom Implementation:**
- 🔧 Predicted pit windows (ML needed)
- 🔧 Rain probability (only actual rainfall available)
- 🔧 Advanced strategy predictions

This provides a solid foundation for race analysis, ML training, and live simulation!
