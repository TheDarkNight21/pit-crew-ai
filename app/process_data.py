import pandas as pd
from typing import Dict, Optional, List
import os
import numpy as np


def create_streamable_race_data(
    laps_df: pd.DataFrame,
    drivers_df: pd.DataFrame,
    stints_df: Optional[pd.DataFrame] = None,
    pit_stops_df: Optional[pd.DataFrame] = None,
    output_path: str = "race_stream_data.csv"
) -> pd.DataFrame:
    """
    Combine all race data sources into a single chronologically-ordered DataFrame
    that can be streamed to simulate live race data.

    This function merges lap times, driver info, tire stints, and pit stops into
    a unified timeline based on timestamps, making it suitable for replaying race
    events in sequence.

    Args:
        laps_df (pd.DataFrame): Lap timing data from fetch_laps()
        drivers_df (pd.DataFrame): Driver metadata from fetch_drivers()
        stints_df (pd.DataFrame, optional): Tire stint data from fetch_stints()
        pit_stops_df (pd.DataFrame, optional): Pit stop data from fetch_pit_stop()
        output_path (str): Path where the CSV file should be saved

    Returns:
        pd.DataFrame: Combined and chronologically sorted DataFrame

    The output DataFrame contains one row per event (lap completion, pit stop, etc.)
    with columns:
        - timestamp: ISO format datetime for chronological ordering
        - event_type: 'lap', 'pit_stop', or 'stint_start'
        - driver_number: Driver number
        - driver_name: Driver acronym (e.g., 'VER', 'HAM')
        - lap_number: Current lap number
        - lap_time: Lap time in seconds (for lap events)
        - lap_duration: Lap duration in seconds
        - is_pit_out_lap: Boolean indicating pit out lap
        - position: Track position
        - compound: Tire compound (SOFT, MEDIUM, HARD)
        - tyre_age_at_start: Age of tires at lap start
        - pit_duration: Pit stop duration in seconds (for pit events)
        - team_name: Team name
        - team_colour: Team color hex code

    Example:
        >>> laps = fetch_laps(session_key)
        >>> drivers = fetch_drivers(session_key)
        >>> stints = fetch_stints(session_key)
        >>> pits = fetch_pit_stop(session_key)
        >>>
        >>> stream_df = create_streamable_race_data(
        ...     laps, drivers, stints, pits,
        ...     output_path="monaco_2025_race.csv"
        ... )
        >>> print(f"Created streamable data with {len(stream_df)} events")
    """

    # Make copies to avoid modifying original dataframes
    laps = laps_df.copy()
    drivers = drivers_df.copy()

    # Prepare driver lookup for merging
    drivers["driver_number"] = drivers["driver_number"].astype(str)
    driver_info = drivers[[
        "driver_number", "name_acronym", "team_name", "team_colour"
    ]].rename(columns={"name_acronym": "driver_name"})

    # Process lap data
    laps["driver_number"] = laps["driver_number"].astype(str)
    laps["event_type"] = "lap"

    # Convert date_start to datetime for proper sorting
    # Use format='ISO8601' to handle varying timestamp formats
    laps["timestamp"] = pd.to_datetime(laps["date_start"], format='ISO8601')

    # Select and rename relevant lap columns
    lap_columns = {
        "timestamp": "timestamp",
        "event_type": "event_type",
        "driver_number": "driver_number",
        "lap_number": "lap_number",
        "lap_duration": "lap_duration",
        "is_pit_out_lap": "is_pit_out_lap",
        "position": "position"
    }

    # Keep only columns that exist
    available_lap_cols = [col for col in lap_columns.keys() if col in laps.columns]
    stream_data = laps[available_lap_cols].copy()

    # Merge driver information
    stream_data = stream_data.merge(driver_info, on="driver_number", how="left")

    # Process stint data if provided
    if stints_df is not None and not stints_df.empty:
        stints = stints_df.copy()
        stints["driver_number"] = stints["driver_number"].astype(str)

        # Merge stint info (compound and tyre age) into lap data based on lap number
        stint_info = stints[[
            "driver_number", "lap_start", "lap_end", "compound", "tyre_age_at_start"
        ]]

        # For each lap, find the matching stint
        def get_stint_info(row):
            driver_stints = stint_info[stint_info["driver_number"] == row["driver_number"]]
            matching_stint = driver_stints[
                (driver_stints["lap_start"] <= row["lap_number"]) &
                (driver_stints["lap_end"] >= row["lap_number"])
            ]
            if not matching_stint.empty:
                stint = matching_stint.iloc[0]
                return pd.Series({
                    "compound": stint["compound"],
                    "tyre_age_at_start": stint["tyre_age_at_start"]
                })
            return pd.Series({"compound": None, "tyre_age_at_start": None})

        stint_data = stream_data.apply(get_stint_info, axis=1)
        stream_data = pd.concat([stream_data, stint_data], axis=1)

    # Process pit stop data if provided
    if pit_stops_df is not None and not pit_stops_df.empty:
        pits = pit_stops_df.copy()
        pits["driver_number"] = pits["driver_number"].astype(str)
        pits["event_type"] = "pit_stop"
        pits["timestamp"] = pd.to_datetime(pits["date"], format='ISO8601')

        # Select relevant pit stop columns
        pit_columns = [
            "timestamp", "event_type", "driver_number",
            "lap_number", "pit_duration"
        ]
        available_pit_cols = [col for col in pit_columns if col in pits.columns]
        pit_events = pits[available_pit_cols].copy()

        # Merge driver info into pit stops
        pit_events = pit_events.merge(driver_info, on="driver_number", how="left")

        # Combine lap events and pit events
        stream_data = pd.concat([stream_data, pit_events], ignore_index=True, sort=False)

    # Sort chronologically by timestamp
    stream_data = stream_data.sort_values("timestamp").reset_index(drop=True)

    # Add a sequential event_id for easy streaming
    stream_data.insert(0, "event_id", range(len(stream_data)))

    # Ensure timestamp is in ISO format string for CSV compatibility
    stream_data["timestamp"] = stream_data["timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S.%f')

    # Save to CSV
    stream_data.to_csv(output_path, index=False)
    print(f" Created streamable race data: {output_path}")
    print(f"  - Total events: {len(stream_data)}")
    print(f"  - Lap events: {len(stream_data[stream_data['event_type'] == 'lap'])}")
    if 'pit_stop' in stream_data['event_type'].values:
        print(f"  - Pit stop events: {len(stream_data[stream_data['event_type'] == 'pit_stop'])}")
    print(f"  - Drivers: {stream_data['driver_number'].nunique()}")

    return stream_data


def stream_race_data(csv_path: str, interval_seconds: float = 1.5, max_events: Optional[int] = None):
    """
    Generator function to stream race data events from a CSV file.

    This simulates receiving live race data by yielding one event at a time
    with a specified time interval between events.

    Args:
        csv_path (str): Path to the streamable race CSV file
        interval_seconds (float): Time delay between events (default: 1.5 seconds)
        max_events (int, optional): Maximum number of events to stream (None = all)

    Yields:
        dict: Each row of race data as a dictionary

    Example:
        >>> for event in stream_race_data("monaco_2025_race.csv", interval_seconds=2.0):
        ...     print(f"[{event['timestamp']}] {event['driver_name']} - {event['event_type']}")
        ...     if event['event_type'] == 'lap':
        ...         print(f"  Lap {event['lap_number']}: {event['lap_duration']}s")
        ...     elif event['event_type'] == 'pit_stop':
        ...         print(f"  Pit stop: {event['pit_duration']}s")
    """
    import time

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    total_events = len(df) if max_events is None else min(max_events, len(df))

    print(f"\n<� Starting race data stream...")
    print(f"   Events to stream: {total_events}")
    print(f"   Interval: {interval_seconds}s between events\n")

    for idx, row in df.head(total_events).iterrows():
        yield row.to_dict()

        # Don't sleep after the last event
        if idx < total_events - 1:
            time.sleep(interval_seconds)


def get_race_summary(csv_path: str) -> Dict:
    """
    Get summary statistics from a streamable race CSV file.

    Args:
        csv_path (str): Path to the streamable race CSV file

    Returns:
        dict: Summary statistics including total events, drivers, laps, etc.

    Example:
        >>> summary = get_race_summary("monaco_2025_race.csv")
        >>> print(f"Race had {summary['total_laps']} laps and {summary['total_pit_stops']} pit stops")
    """
    df = pd.read_csv(csv_path)

    summary = {
        "total_events": len(df),
        "total_laps": len(df[df["event_type"] == "lap"]),
        "total_pit_stops": len(df[df["event_type"] == "pit_stop"]) if "pit_stop" in df["event_type"].values else 0,
        "number_of_drivers": df["driver_number"].nunique(),
        "race_duration_estimate": f"{len(df[df['event_type'] == 'lap']) * 1.5 / 60:.1f} minutes (at 1.5s/event)",
        "first_event": df["timestamp"].iloc[0] if not df.empty else None,
        "last_event": df["timestamp"].iloc[-1] if not df.empty else None,
    }

    return summary


def create_telemetry_race_data(
    laps_df: pd.DataFrame,
    drivers_df: pd.DataFrame,
    car_data_df: Optional[pd.DataFrame] = None,
    intervals_df: Optional[pd.DataFrame] = None,
    weather_df: Optional[pd.DataFrame] = None,
    race_control_df: Optional[pd.DataFrame] = None,
    position_df: Optional[pd.DataFrame] = None,
    stints_df: Optional[pd.DataFrame] = None,
    pit_stops_df: Optional[pd.DataFrame] = None,
    output_path: str = "race_telemetry_data.csv"
) -> pd.DataFrame:
    """
    Create comprehensive telemetry-enriched race data combining lap events with
    high-frequency car data, weather, race control events, and derived metrics.

    This function creates a detailed CSV suitable for machine learning and race
    analysis by merging multiple data sources at different sampling rates.

    Args:
        laps_df: Lap timing data (one row per lap)
        drivers_df: Driver metadata
        car_data_df: Car telemetry (speed, throttle, brake, rpm, gear, drs) ~3.7 Hz
        intervals_df: Gap data (gap_to_leader, interval) ~0.25 Hz
        weather_df: Track conditions (temps, wind, rainfall) ~0.017 Hz
        race_control_df: Flags, safety cars, penalties
        position_df: Position changes
        stints_df: Tire stint information
        pit_stops_df: Pit stop events
        output_path: Output CSV file path

    Returns:
        pd.DataFrame: Combined telemetry data sorted chronologically

    Output includes:
        - All lap-based fields (lap_number, lap_duration, position, etc.)
        - Car telemetry (speed, throttle, brake, rpm, gear, drs)
        - Gap data (gap_to_leader, gap_to_car_ahead)
        - Weather (air_temp, track_temp, rainfall, humidity, wind)
        - Track status derived from race control
        - Tire information (compound, age)
        - Event types (lap, pit_in, pit_out, yellow_flag, vsc, safety_car, etc.)
        - Derived metrics (delta_vs_best_lap, gap_to_car_behind)
    """

    print(f"\n🏎️  Creating telemetry-enriched race data...")

    # Prepare driver lookup
    drivers = drivers_df.copy()
    drivers["driver_number"] = drivers["driver_number"].astype(str)
    driver_info = drivers[[
        "driver_number", "name_acronym", "team_name", "team_colour"
    ]].rename(columns={"name_acronym": "driver_name"})

    # ========== Process Lap Events ==========
    laps = laps_df.copy()
    laps["driver_number"] = laps["driver_number"].astype(str)
    laps["timestamp"] = pd.to_datetime(laps["date_start"], format='ISO8601')
    laps["event_type"] = "lap"

    # Calculate delta vs best lap for each driver
    laps["delta_vs_best_lap"] = laps.groupby("driver_number")["lap_duration"].transform(
        lambda x: x - x.min() if x.notna().any() else np.nan
    )

    # Select lap columns (only those that exist)
    lap_columns_wanted = [
        "timestamp", "event_type", "driver_number", "lap_number",
        "lap_duration", "is_pit_out_lap", "position", "delta_vs_best_lap"
    ]
    lap_columns_available = [col for col in lap_columns_wanted if col in laps.columns]
    lap_events = laps[lap_columns_available].copy()

    # ========== Process Race Control Events ==========
    race_control_events = pd.DataFrame()
    if race_control_df is not None and not race_control_df.empty:
        rc = race_control_df.copy()
        rc["timestamp"] = pd.to_datetime(rc["date"], format='ISO8601')
        rc["driver_number"] = rc["driver_number"].astype(str).fillna("")

        # Map race control messages to event types
        def categorize_race_control_event(row):
            msg = str(row.get("message", "")).lower()
            flag = str(row.get("flag", "")).lower()
            category = str(row.get("category", "")).lower()

            if "yellow" in flag or "yellow" in msg:
                return "yellow_flag"
            elif "green" in flag or "green" in msg:
                return "green_flag"
            elif "red" in flag or "red" in msg:
                return "red_flag"
            elif "vsc" in msg or "virtual safety car" in msg:
                return "vsc" if "deployed" in msg or "start" in msg else "vsc_end"
            elif "safety car" in msg:
                return "safety_car" if "deployed" in msg else "safety_car_end"
            elif "rain" in msg:
                return "rain_start" if "start" in msg or "detected" in msg else "rain_end"
            else:
                return "race_control"

        rc["event_type"] = rc.apply(categorize_race_control_event, axis=1)

        race_control_events = rc[[
            "timestamp", "event_type", "driver_number", "lap_number",
            "message", "flag", "category", "scope", "sector"
        ]].copy()

        print(f"  ✓ Processed {len(race_control_events)} race control events")

    # ========== Process Pit Stop Events ==========
    pit_events = pd.DataFrame()
    if pit_stops_df is not None and not pit_stops_df.empty:
        pits = pit_stops_df.copy()
        pits["driver_number"] = pits["driver_number"].astype(str)
        pits["timestamp"] = pd.to_datetime(pits["date"], format='ISO8601')

        # Create pit_in and pit_out events
        pit_in = pits.copy()
        pit_in["event_type"] = "pit_in"

        pit_out = pits.copy()
        pit_out["event_type"] = "pit_out"
        # Pit out timestamp = pit in + pit duration
        pit_out["timestamp"] = pit_out["timestamp"] + pd.to_timedelta(
            pit_out["pit_duration"], unit='s'
        )

        pit_events = pd.concat([pit_in, pit_out], ignore_index=True)
        pit_events = pit_events[[
            "timestamp", "event_type", "driver_number", "lap_number", "pit_duration"
        ]].copy()

        print(f"  ✓ Processed {len(pit_stops_df)} pit stops ({len(pit_events)} events)")

    # ========== Combine All Events ==========
    all_events = pd.concat([
        lap_events,
        race_control_events,
        pit_events
    ], ignore_index=True, sort=False)

    # Filter out rows with null timestamps (shouldn't happen, but just in case)
    all_events = all_events.dropna(subset=["timestamp"])

    all_events = all_events.sort_values("timestamp").reset_index(drop=True)
    all_events["event_id"] = range(len(all_events))

    # Merge driver info
    all_events = all_events.merge(driver_info, on="driver_number", how="left")

    # ========== Add Telemetry Data via Time-Based Merge ==========
    if car_data_df is not None and not car_data_df.empty:
        car_data = car_data_df.copy()
        car_data["driver_number"] = car_data["driver_number"].astype(str)
        car_data["timestamp"] = pd.to_datetime(car_data["date"], format='ISO8601')

        print(f"  ⚙️  Merging {len(car_data)} car telemetry samples...")

        # Only merge car data for events with driver numbers
        has_driver = all_events["driver_number"].notna() & (all_events["driver_number"] != "")
        events_with_driver = all_events[has_driver].copy()
        events_without_driver = all_events[~has_driver].copy()

        if not events_with_driver.empty:
            events_with_driver = pd.merge_asof(
                events_with_driver.sort_values("timestamp"),
                car_data[["timestamp", "driver_number", "speed", "throttle", "brake",
                         "rpm", "n_gear", "drs"]].sort_values("timestamp"),
                on="timestamp",
                by="driver_number",
                direction="nearest",
                tolerance=pd.Timedelta(seconds=5)
            )

            # Recombine all events
            all_events = pd.concat([events_with_driver, events_without_driver], ignore_index=True)
            all_events = all_events.sort_values("timestamp").reset_index(drop=True)

        print(f"  ✓ Car telemetry merged")

    # ========== Add Interval/Gap Data ==========
    if intervals_df is not None and not intervals_df.empty:
        intervals = intervals_df.copy()
        intervals["driver_number"] = intervals["driver_number"].astype(str)
        intervals["timestamp"] = pd.to_datetime(intervals["date"], format='ISO8601')

        print(f"  📊 Merging {len(intervals)} interval samples...")

        # Split events into those with and without driver_number
        # (race control events may not have driver_number)
        has_driver = all_events["driver_number"].notna() & (all_events["driver_number"] != "")
        events_with_driver = all_events[has_driver].copy()
        events_without_driver = all_events[~has_driver].copy()

        if not events_with_driver.empty:
            # Merge intervals only for events with driver numbers
            valid_intervals = intervals[["timestamp", "driver_number", "gap_to_leader", "interval"]].dropna(subset=["timestamp", "driver_number"])

            events_with_driver = pd.merge_asof(
                events_with_driver.sort_values("timestamp"),
                valid_intervals.sort_values("timestamp"),
                on="timestamp",
                by="driver_number",
                direction="nearest",
                tolerance=pd.Timedelta(seconds=10)
            )

            # Rename interval to gap_to_car_ahead for clarity
            events_with_driver = events_with_driver.rename(columns={"interval": "gap_to_car_ahead"})

            # Calculate gap_to_car_behind (only if position column exists)
            if "position" in events_with_driver.columns:
                events_with_driver = events_with_driver.sort_values(["timestamp", "position"])
                events_with_driver["gap_to_car_behind"] = events_with_driver.groupby("timestamp")["gap_to_car_ahead"].shift(-1)

            # Recombine all events
            all_events = pd.concat([events_with_driver, events_without_driver], ignore_index=True)
            all_events = all_events.sort_values("timestamp").reset_index(drop=True)

        print(f"  ✓ Gap data merged")

    # ========== Add Weather Data ==========
    if weather_df is not None and not weather_df.empty:
        weather = weather_df.copy()
        weather["timestamp"] = pd.to_datetime(weather["date"], format='ISO8601')

        print(f"  🌤️  Merging {len(weather)} weather samples...")
        # Weather applies to all drivers, so merge without 'by' parameter
        all_events = pd.merge_asof(
            all_events.sort_values("timestamp"),
            weather[["timestamp", "air_temperature", "track_temperature",
                    "humidity", "pressure", "rainfall", "wind_speed", "wind_direction"]].sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta(minutes=2)
        )
        print(f"  ✓ Weather data merged")

    # ========== Add Position Data (Higher Granularity) ==========
    if position_df is not None and not position_df.empty:
        positions = position_df.copy()
        positions["driver_number"] = positions["driver_number"].astype(str)
        positions["timestamp"] = pd.to_datetime(positions["date"], format='ISO8601')

        # Only use position data if we don't already have it from laps
        if "position" not in all_events.columns or all_events["position"].isna().all():
            print(f"  🏁 Merging {len(positions)} position samples...")

            # Only merge position for events with driver numbers
            has_driver = all_events["driver_number"].notna() & (all_events["driver_number"] != "")
            events_with_driver = all_events[has_driver].copy()
            events_without_driver = all_events[~has_driver].copy()

            if not events_with_driver.empty:
                events_with_driver = pd.merge_asof(
                    events_with_driver.sort_values("timestamp"),
                    positions[["timestamp", "driver_number", "position"]].sort_values("timestamp"),
                    on="timestamp",
                    by="driver_number",
                    direction="nearest",
                    tolerance=pd.Timedelta(seconds=5)
                )

                # Recombine all events
                all_events = pd.concat([events_with_driver, events_without_driver], ignore_index=True)
                all_events = all_events.sort_values("timestamp").reset_index(drop=True)

            print(f"  ✓ Position data merged")

    # ========== Add Stint/Tire Data ==========
    if stints_df is not None and not stints_df.empty:
        stints = stints_df.copy()
        stints["driver_number"] = stints["driver_number"].astype(str)

        # Merge tire info based on lap number
        def get_tire_info(row):
            if pd.isna(row.get("lap_number")):
                return pd.Series({"compound": None, "tyre_age_at_start": None})

            driver_stints = stints[stints["driver_number"] == row["driver_number"]]
            matching = driver_stints[
                (driver_stints["lap_start"] <= row["lap_number"]) &
                (driver_stints["lap_end"] >= row["lap_number"])
            ]
            if not matching.empty:
                stint = matching.iloc[0]
                return pd.Series({
                    "compound": stint["compound"],
                    "tyre_age_at_start": stint["tyre_age_at_start"]
                })
            return pd.Series({"compound": None, "tyre_age_at_start": None})

        print(f"  🛞 Adding tire stint information...")
        tire_data = all_events.apply(get_tire_info, axis=1)
        all_events = pd.concat([all_events, tire_data], axis=1)
        print(f"  ✓ Tire data added")

    # ========== Derive Track Status ==========
    # Create track_status field based on race control events
    all_events["track_status"] = "green"

    if not race_control_events.empty:
        for idx, row in all_events.iterrows():
            # Find the most recent race control event before this timestamp
            prior_events = all_events[
                (all_events["timestamp"] <= row["timestamp"]) &
                (all_events["event_type"].isin(["yellow_flag", "green_flag", "vsc",
                                                 "vsc_end", "safety_car", "safety_car_end"]))
            ]
            if not prior_events.empty:
                last_event = prior_events.iloc[-1]
                if last_event["event_type"] in ["yellow_flag"]:
                    all_events.at[idx, "track_status"] = "yellow"
                elif last_event["event_type"] in ["vsc"]:
                    all_events.at[idx, "track_status"] = "vsc"
                elif last_event["event_type"] in ["safety_car"]:
                    all_events.at[idx, "track_status"] = "safety_car"

    # ========== Final Cleanup ==========
    # Sort by timestamp
    all_events = all_events.sort_values("timestamp").reset_index(drop=True)

    # Convert timestamp to string for CSV
    all_events["timestamp"] = all_events["timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S.%f')

    # Save to CSV
    all_events.to_csv(output_path, index=False)

    # Print summary
    print(f"\n✅ Created telemetry race data: {output_path}")
    print(f"  - Total events: {len(all_events)}")
    print(f"  - Event types: {all_events['event_type'].value_counts().to_dict()}")
    print(f"  - Drivers: {all_events['driver_number'].nunique()}")
    print(f"  - Columns: {len(all_events.columns)}")
    print(f"  - Available fields:")
    for col in all_events.columns:
        non_null = all_events[col].notna().sum()
        if non_null > 0:
            print(f"    • {col}: {non_null}/{len(all_events)} records")

    return all_events
