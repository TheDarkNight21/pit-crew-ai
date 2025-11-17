"""
Example script demonstrating how to load comprehensive telemetry data from OpenF1.

This script shows how to:
1. Fetch all available data endpoints for a race
2. Create a comprehensive telemetry CSV with car data, weather, race events
3. Includes event types: lap, pit_in, pit_out, yellow_flag, vsc, safety_car, etc.
"""

from app.data_loader import (
    fetch_sessions,
    fetch_laps,
    fetch_stints,
    fetch_pit_stop,
    fetch_drivers,
    fetch_car_data,
    fetch_intervals,
    fetch_weather,
    fetch_race_control,
    fetch_position,
)
from app.process_data import create_telemetry_race_data

# Configuration
YEAR = 2025
COUNTRY = "Monaco"
MEETING_NAME = "Monaco Grand Prix - Monaco"
SESSION_NAME = "Race"  # Can be: Practice 1, Practice 2, Practice 3, Qualifying, Sprint, Race

def main():
    # Import here to avoid issues if not installed
    from app.data_loader import fetch_data

    print(f"\n{'='*60}")
    print(f"🏎️  OpenF1 Telemetry Data Loader")
    print(f"{'='*60}\n")

    # Step 1: Get meeting
    print(f"📍 Fetching {YEAR} {COUNTRY} Grand Prix...")
    all_meetings = fetch_data("meetings", {"year": YEAR})
    filtered_meetings = all_meetings[all_meetings["country_name"] == COUNTRY].copy()

    if filtered_meetings.empty:
        print(f"❌ No meetings found for {COUNTRY} in {YEAR}")
        return

    filtered_meetings["label"] = filtered_meetings["meeting_name"] + " - " + filtered_meetings["location"]
    selected_meeting_key = filtered_meetings.iloc[0]["meeting_key"]
    print(f"   ✓ Found meeting_key: {selected_meeting_key}")

    # Step 2: Get session
    print(f"\n📅 Fetching sessions...")
    sessions = fetch_sessions(selected_meeting_key)
    sessions["session_type"] = sessions["label"].str.extract(r"^(.*?)\s\(")

    race_session = sessions[sessions["session_type"] == SESSION_NAME]
    if race_session.empty:
        print(f"❌ No {SESSION_NAME} session found")
        print(f"Available sessions: {sessions['session_type'].unique()}")
        return

    session_key = race_session.iloc[0]["session_key"]
    print(f"   ✓ Found {SESSION_NAME} session_key: {session_key}")

    # Step 3: Fetch all data sources
    print(f"\n📊 Fetching data from OpenF1 API...")
    print(f"   This may take a while for large datasets...\n")

    # Core data (always needed)
    print("   → Fetching drivers...")
    drivers_df = fetch_drivers(session_key)
    print(f"      ✓ {len(drivers_df)} drivers")

    print("   → Fetching laps...")
    laps_df = fetch_laps(session_key)
    print(f"      ✓ {len(laps_df)} lap records")

    # Optional but recommended
    print("   → Fetching stints (tire data)...")
    stints_df = fetch_stints(session_key)
    print(f"      ✓ {len(stints_df)} stint records")

    print("   → Fetching pit stops...")
    pit_stops_df = fetch_pit_stop(session_key)
    print(f"      ✓ {len(pit_stops_df)} pit stops")

    # Telemetry data (high frequency) - May not be available for all sessions
    print("   → Fetching car telemetry (speed, throttle, brake, rpm, gear, drs)...")
    car_data_df = fetch_car_data(session_key, raise_on_error=False)
    if car_data_df.empty:
        print(f"      ⚠️  Car telemetry not available for this session")
    else:
        print(f"      ✓ {len(car_data_df)} telemetry samples (~3.7 Hz)")

    # Gap/interval data - Only available for race sessions
    print("   → Fetching intervals (gaps between cars)...")
    intervals_df = fetch_intervals(session_key, raise_on_error=False)
    if intervals_df.empty:
        print(f"      ⚠️  Interval data not available (race sessions only)")
    else:
        print(f"      ✓ {len(intervals_df)} interval samples")

    # Weather data
    print("   → Fetching weather data...")
    weather_df = fetch_weather(session_key, raise_on_error=False)
    if weather_df.empty:
        print(f"      ⚠️  Weather data not available for this session")
    else:
        print(f"      ✓ {len(weather_df)} weather samples")

    # Race control (flags, safety cars, etc.)
    print("   → Fetching race control messages...")
    race_control_df = fetch_race_control(session_key, raise_on_error=False)
    if race_control_df.empty:
        print(f"      ⚠️  Race control data not available for this session")
    else:
        print(f"      ✓ {len(race_control_df)} race control events")

    # Position data
    print("   → Fetching position data...")
    position_df = fetch_position(session_key, raise_on_error=False)
    if position_df.empty:
        print(f"      ⚠️  Position data not available for this session")
    else:
        print(f"      ✓ {len(position_df)} position samples")

    # Step 4: Process and combine all data
    output_file = f"telemetry_{COUNTRY.lower()}_{YEAR}_{SESSION_NAME.lower()}.csv"

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
        output_path=output_file
    )

    # Step 5: Display summary
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS - Telemetry data ready!")
    print(f"{'='*60}\n")
    print(f"📄 Output file: {output_file}")
    print(f"\n📈 Data Summary:")
    print(f"   • Total events: {len(telemetry_df):,}")
    print(f"   • Drivers: {telemetry_df['driver_number'].nunique()}")
    print(f"   • Columns: {len(telemetry_df.columns)}")

    print(f"\n🎯 Event Types:")
    event_counts = telemetry_df['event_type'].value_counts()
    for event_type, count in event_counts.items():
        print(f"   • {event_type}: {count}")

    print(f"\n🔧 Available Fields:")
    print(f"   Car State:")
    for field in ['speed', 'throttle', 'brake', 'rpm', 'n_gear', 'drs', 'gap_to_car_ahead', 'gap_to_car_behind', 'gap_to_leader']:
        if field in telemetry_df.columns:
            non_null = telemetry_df[field].notna().sum()
            if non_null > 0:
                print(f"      • {field}: {non_null:,} records")

    print(f"\n   Track Conditions:")
    for field in ['air_temperature', 'track_temperature', 'rainfall', 'humidity', 'wind_speed', 'track_status']:
        if field in telemetry_df.columns:
            non_null = telemetry_df[field].notna().sum()
            if non_null > 0:
                print(f"      • {field}: {non_null:,} records")

    print(f"\n   Tire Info:")
    for field in ['compound', 'tyre_age_at_start']:
        if field in telemetry_df.columns:
            non_null = telemetry_df[field].notna().sum()
            if non_null > 0:
                print(f"      • {field}: {non_null:,} records")

    print(f"\n   Derived Metrics:")
    for field in ['delta_vs_best_lap']:
        if field in telemetry_df.columns:
            non_null = telemetry_df[field].notna().sum()
            if non_null > 0:
                print(f"      • {field}: {non_null:,} records")

    print(f"\n💡 Next Steps:")
    print(f"   1. Load the CSV: pd.read_csv('{output_file}')")
    print(f"   2. Use for ML training, race analysis, or live simulation")
    print(f"   3. Filter by driver_number or event_type for specific analysis")

    # Check if critical data is missing
    missing_data = []
    if car_data_df.empty:
        missing_data.append("car telemetry")
    if intervals_df.empty:
        missing_data.append("intervals")
    if weather_df.empty:
        missing_data.append("weather")

    if missing_data:
        print(f"\n⚠️  Note: Some data was not available for this session:")
        for data in missing_data:
            print(f"   • {data}")
        print(f"\n   Try different sessions/years for more complete data:")
        print(f"   • 2024 sessions often have more complete telemetry")
        print(f"   • Practice/Qualifying sessions may have limited data")
        print(f"   • Edit YEAR and SESSION_NAME at top of this script")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
