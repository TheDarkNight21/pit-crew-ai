"""
Example script with caching and rate limit handling.

This version uses smart_fetch() to automatically:
- Cache results locally to avoid repeated API calls
- Retry with exponential backoff if rate limited
- Handle errors gracefully
"""

import sys
from pathlib import Path
import time
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data_loader import (
    fetch_data,
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
from app.api_helpers import smart_fetch, clear_cache

# Configuration
YEAR = 2025
COUNTRY = "Monaco"
SESSION_NAME = "Race"
USE_CACHE = True  # Set to False to force fresh API calls

def main():
    print(f"\n{'='*60}")
    print(f"🏎️  OpenF1 Telemetry Loader (with Caching)")
    print(f"{'='*60}\n")

    # Step 1: Get meeting (no caching for metadata)
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

    # Create cache prefix for this session
    cache_prefix = f"{COUNTRY.lower()}_{YEAR}_{SESSION_NAME.lower()}"

    # Step 3: Fetch all data with smart caching
    print(f"\n📊 Fetching data (cache: {'enabled' if USE_CACHE else 'disabled'})...")

    print("   → Fetching drivers...")
    drivers_df = smart_fetch(
        fetch_drivers, f"{cache_prefix}_drivers",
        use_cache=USE_CACHE, session_key=session_key
    )
    print(f"      ✓ {len(drivers_df)} drivers")

    print("   → Fetching laps...")
    laps_df = smart_fetch(
        fetch_laps, f"{cache_prefix}_laps",
        use_cache=USE_CACHE, session_key=session_key
    )
    print(f"      ✓ {len(laps_df)} lap records")

    print("   → Fetching stints...")
    stints_df = smart_fetch(
        fetch_stints, f"{cache_prefix}_stints",
        use_cache=USE_CACHE, session_key=session_key
    )
    print(f"      ✓ {len(stints_df)} stint records")

    print("   → Fetching pit stops...")
    pit_stops_df = smart_fetch(
        fetch_pit_stop, f"{cache_prefix}_pitstops",
        use_cache=USE_CACHE, session_key=session_key
    )
    print(f"      ✓ {len(pit_stops_df)} pit stops")

    # Optional data - may not be available
    # Fetch car telemetry per driver to avoid "too much data" error
    print("   → Fetching car telemetry...")
    print("      (Fetching per driver to avoid API limits)\n")

    all_car_data = []
    driver_numbers = sorted(drivers_df['driver_number'].unique())

    for idx, driver_num in enumerate(driver_numbers, 1):
        print(f"      [{idx}/{len(driver_numbers)}] Driver {driver_num}...", end=" ", flush=True)

        try:
            driver_car_data = smart_fetch(
                lambda sk, dn=driver_num: fetch_car_data(sk, driver_number=dn, raise_on_error=False),
                f"{cache_prefix}_cardata_driver{driver_num}",
                use_cache=USE_CACHE, session_key=session_key
            )
            if not driver_car_data.empty:
                all_car_data.append(driver_car_data)
                print(f"✓ {len(driver_car_data):,} samples")
            else:
                print("⚠️ No data")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Rate limit: wait 1 second between drivers (except after last one)
        if idx < len(driver_numbers):
            time.sleep(1)

    # Combine all driver data
    if all_car_data:
        car_data_df = pd.concat(all_car_data, ignore_index=True)
        print(f"\n      ✓ Total: {len(car_data_df):,} telemetry samples")
    else:
        car_data_df = pd.DataFrame()
        print(f"\n      ⚠️  Car telemetry not available")

    print("   → Fetching intervals...")
    intervals_df = smart_fetch(
        lambda sk: fetch_intervals(sk, raise_on_error=False),
        f"{cache_prefix}_intervals",
        use_cache=USE_CACHE, session_key=session_key
    )
    if intervals_df.empty:
        print(f"      ⚠️  Interval data not available")
    else:
        print(f"      ✓ {len(intervals_df)} interval samples")

    print("   → Fetching weather...")
    weather_df = smart_fetch(
        lambda sk: fetch_weather(sk, raise_on_error=False),
        f"{cache_prefix}_weather",
        use_cache=USE_CACHE, session_key=session_key
    )
    if weather_df.empty:
        print(f"      ⚠️  Weather data not available")
    else:
        print(f"      ✓ {len(weather_df)} weather samples")

    print("   → Fetching race control...")
    race_control_df = smart_fetch(
        lambda sk: fetch_race_control(sk, raise_on_error=False),
        f"{cache_prefix}_racecontrol",
        use_cache=USE_CACHE, session_key=session_key
    )
    if race_control_df.empty:
        print(f"      ⚠️  Race control data not available")
    else:
        print(f"      ✓ {len(race_control_df)} race control events")

    print("   → Fetching position...")
    position_df = smart_fetch(
        lambda sk: fetch_position(sk, raise_on_error=False),
        f"{cache_prefix}_position",
        use_cache=USE_CACHE, session_key=session_key
    )
    if position_df.empty:
        print(f"      ⚠️  Position data not available")
    else:
        print(f"      ✓ {len(position_df)} position samples")

    # Step 4: Process and combine
    output_file = f"telemetry_{cache_prefix}.csv"

    telemetry_df = create_telemetry_race_data(
        laps_df=laps_df,
        drivers_df=drivers_df,
        car_data_df=car_data_df if not car_data_df.empty else None,
        intervals_df=intervals_df if not intervals_df.empty else None,
        weather_df=weather_df if not weather_df.empty else None,
        race_control_df=race_control_df if not race_control_df.empty else None,
        position_df=position_df if not position_df.empty else None,
        stints_df=stints_df if not stints_df.empty else None,
        pit_stops_df=pit_stops_df if not pit_stops_df.empty else None,
        output_path=output_file
    )

    # Step 5: Summary
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS")
    print(f"{'='*60}\n")
    print(f"📄 Output: {output_file}")
    print(f"📦 Cache: ./cache/{cache_prefix}_*.pkl")

    # Check for missing data
    missing_data = []
    if car_data_df.empty:
        missing_data.append("car telemetry")
    if intervals_df.empty:
        missing_data.append("intervals")
    if weather_df.empty:
        missing_data.append("weather")

    if missing_data:
        print(f"\n⚠️  Missing data: {', '.join(missing_data)}")
        print(f"   Try 2024 sessions for more complete data")

    print(f"\n💡 To clear cache: python -c \"from app.api_helpers import clear_cache; clear_cache()\"")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
