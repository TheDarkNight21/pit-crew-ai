from app.data_loader import (
    fetch_data,
    fetch_sessions,
    fetch_laps,
    fetch_stints,
    fetch_pit_stop,
    fetch_drivers
)

# Step 1: Select Year and Country dynamically
available_years = [2025]

# Fetch all meetings for selected year
all_meetings = fetch_data("meetings", {"year": 2025})

selected_meeting = "Monaco Grand Prix - Monaco"

# print(all_meetings)

if all_meetings.empty:
    print("No meetings found for this year.")

available_countries = sorted(all_meetings["country_name"].dropna().unique())
selected_country = "Monaco"

# Filter meetings for selected year and country
filtered_meetings = all_meetings[all_meetings["country_name"] == selected_country].copy()
filtered_meetings["label"] = filtered_meetings["meeting_name"] + " - " + filtered_meetings["location"]
filtered_meetings = filtered_meetings.sort_values(by="meeting_key", ascending=False)

# print(filtered_meetings)

selected_meeting_key = filtered_meetings.loc[
        filtered_meetings["label"] == selected_meeting, "meeting_key"
    ].values[0]

sessions = fetch_sessions(selected_meeting_key)
print(sessions)

sessions["session_type"] = sessions["label"].str.extract(r"^(.*?)\s\(")

selected_session = "Race (2025-05-25T13:00:00+00:00)"
selected_session_type = sessions.loc[sessions["label"] == selected_session, "session_type"].values[0]
selected_session_key = sessions.loc[sessions["label"] == selected_session, "session_key"].values[0]

# print(selected_session_key)
# print(selected_session_type)

# Fetch and preprocess driver info
driver_df = fetch_drivers(selected_session_key)
driver_df["driver_number"] = driver_df["driver_number"].astype(str)
driver_info = driver_df[["driver_number", "name_acronym"]]

lap_df = fetch_laps(selected_session_key)
print(lap_df)
# processed_df = process_lap_data(lap_df)

# # Merge name_acronym into the lap data
# processed_df["driver_number"] = processed_df["driver_number"].astype(str)
# processed_df = processed_df.merge(driver_info, on="driver_number", how="left")

# if processed_df.empty:
#     print("No lap time data found.")