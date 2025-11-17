import pandas as pd
from typing import Dict, Optional
import os


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
