"""
Example script demonstrating how to create and stream race data.

This script shows how to:
1. Fetch race data from the API
2. Combine it into a streamable CSV file
3. Stream the data to simulate live race updates
"""

from app.data_loader import (
    fetch_sessions,
    fetch_laps,
    fetch_stints,
    fetch_pit_stop,
    fetch_drivers,
    fetch_data
)
from app.process_data import (
    create_streamable_race_data,
    stream_race_data,
    get_race_summary
)


def main():
    # Configuration
    year = 2025
    country = "Monaco"
    selected_meeting = "Monaco Grand Prix - Monaco"
    selected_session = "Race (2025-05-25T13:00:00+00:00)"

    print(f"🏎️  Fetching race data for {selected_meeting}...")

    # Step 1: Get meeting and session keys
    all_meetings = fetch_data("meetings", {"year": year})

    if all_meetings.empty:
        print("❌ No meetings found for this year.")
        return

    # Filter for specific country and meeting
    filtered_meetings = all_meetings[all_meetings["country_name"] == country].copy()
    filtered_meetings["label"] = filtered_meetings["meeting_name"] + " - " + filtered_meetings["location"]

    selected_meeting_key = filtered_meetings.loc[
        filtered_meetings["label"] == selected_meeting, "meeting_key"
    ].values[0]

    # Get sessions
    sessions = fetch_sessions(selected_meeting_key)
    selected_session_key = sessions.loc[sessions["label"] == selected_session, "session_key"].values[0]

    print(f"   Meeting Key: {selected_meeting_key}")
    print(f"   Session Key: {selected_session_key}\n")

    # Step 2: Fetch all race data
    print("📊 Fetching race data from API...")
    laps_df = fetch_laps(selected_session_key)
    drivers_df = fetch_drivers(selected_session_key)
    stints_df = fetch_stints(selected_session_key)
    pit_stops_df = fetch_pit_stop(selected_session_key)

    print(f"   Laps: {len(laps_df)}")
    print(f"   Drivers: {len(drivers_df)}")
    print(f"   Stints: {len(stints_df)}")
    print(f"   Pit Stops: {len(pit_stops_df)}\n")

    # Step 3: Create streamable CSV
    print("🔄 Creating streamable race data file...")
    output_file = "monaco_2025_race_stream.csv"

    stream_df = create_streamable_race_data(
        laps_df=laps_df,
        drivers_df=drivers_df,
        stints_df=stints_df,
        pit_stops_df=pit_stops_df,
        output_path=output_file
    )

    # Step 4: Get summary
    print("\n📈 Race Summary:")
    summary = get_race_summary(output_file)
    for key, value in summary.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")

    # Step 5: Demo streaming (first 20 events)
    print("\n" + "="*60)
    print("🎥 DEMO: Streaming first 20 events (1.5s intervals)")
    print("="*60 + "\n")

    event_count = 0
    for event in stream_race_data(output_file, interval_seconds=1.5, max_events=20):
        event_count += 1

        # Format output based on event type
        timestamp = event['timestamp'].split('.')[0]  # Remove microseconds
        driver = event.get('driver_name', 'Unknown')

        if event['event_type'] == 'lap':
            lap_num = event.get('lap_number', 'N/A')
            lap_time = event.get('lap_duration', 'N/A')
            position = event.get('position', 'N/A')
            compound = event.get('compound', 'N/A')

            print(f"[{timestamp}] LAP {lap_num:>2} | {driver:>3} | P{position:>2} | "
                  f"{lap_time:>6.2f}s | {compound}")

        elif event['event_type'] == 'pit_stop':
            lap_num = event.get('lap_number', 'N/A')
            pit_time = event.get('pit_duration', 'N/A')

            print(f"[{timestamp}] PIT STOP | {driver:>3} | Lap {lap_num:>2} | "
                  f"Duration: {pit_time:.2f}s")

    print(f"\n✓ Streamed {event_count} events")
    print(f"\n💾 Full race data saved to: {output_file}")
    print(f"   Use stream_race_data('{output_file}') to replay the entire race!\n")


if __name__ == "__main__":
    main()
