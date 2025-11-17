import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.getenv("BASE_API_URL")


def fetch_data(endpoint, params=None, raise_on_error=True):
    """
    Fetch data from the OpenF1 API and return it as a DataFrame.

    Args:
        endpoint (str): API endpoint (e.g., "meetings", "sessions").
        params (dict): Optional query parameters for the API.
        raise_on_error (bool): If False, return empty DataFrame on error instead of raising.

    Returns:
        pd.DataFrame: DataFrame containing the API response data.

    Notes:
        The OpenF1 API requires properly URL-encoded query strings,
        especially when using complex filters (e.g., strings with spaces).
        Using `requests.get(url, params=params)` sometimes causes issues with
        formatting, so we manually prepare the full URL using `requests.Request`.
    """
    if params is None:
        params = {}

    url = f"{BASE_URL}{endpoint}"
    full_url = requests.Request('GET', url, params=params).prepare().url

    try:
        response = requests.get(full_url)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except requests.exceptions.HTTPError:
        if raise_on_error:
            raise
        else:
            # Return empty DataFrame on error
            return pd.DataFrame()


# Cached API calls using Streamlit's cache_data decorator

#@st.cache_data
def fetch_meetings(year, country):
    # The 'meetings' endpoint returns all information for a specified meeting (Miami, Monaco, Imola, etc)
    # for a specified year (2023, 2024, etc).
    df = fetch_data("meetings", {"year": year, "country_name": country})
    if df.empty:
        #st.error("⚠️ No meeting data found.")
        return pd.DataFrame()

    # Create a label for easier dropdown display
    df["label"] = df["meeting_name"] + " - " + df["location"]
    df = df.sort_values(by="meeting_key", ascending=False)

    # Return minimal relevant fields
    return df[["meeting_key", "label", "year"]].drop_duplicates()


#@st.cache_data
def fetch_sessions(meeting_key):
    # The 'sessions' endpoint returns all session types (FP1, Qualifying, Race) for a specific Grand Prix.
    # Filtered here using 'meeting_key' from the 'meetings' endpoint.
    df = fetch_data("sessions", {"meeting_key": meeting_key})

    # Combine session name and start date for display
    df["label"] = df["session_name"] + " (" + df["date_start"] + ")"

    # Only keep necessary columns for dropdowns
    return df[["session_key", "label"]].drop_duplicates()


#@st.cache_data
def fetch_laps(session_key):
    # Retrieves detailed lap timing data for a given session
    return fetch_data("laps", {"session_key": session_key})


#@st.cache_data
def fetch_stints(session_key):
    # Fetches tire stint data, which includes tire compound and start/end laps
    return fetch_data("stints", {"session_key": session_key})


#@st.cache_data
def fetch_pit_stop(session_key):
    # Returns pit stop information, including duration and lap number
    return fetch_data("pit", {"session_key": session_key})


#@st.cache_data
def fetch_drivers(session_key):
    # Provides driver metadata such as name, number, and team color
    return fetch_data("drivers", {"session_key": session_key})


#@st.cache_data
def fetch_car_data(session_key, driver_number=None, raise_on_error=False):
    """
    Fetches car telemetry data including speed, throttle, brake, RPM, gear, and DRS.
    Sampled at approximately 3.7 Hz.

    Args:
        session_key: Session identifier
        driver_number: Optional driver number to filter (can be int or str)
        raise_on_error: If False, returns empty DataFrame when data unavailable

    Returns:
        DataFrame with columns: date, driver_number, speed, throttle, brake,
                                rpm, n_gear, drs, session_key, meeting_key

    Note:
        Car data may not be available for all sessions. OpenF1 provides this
        data "shortly after each session" but availability varies.
    """
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return fetch_data("car_data", params, raise_on_error=raise_on_error)


#@st.cache_data
def fetch_intervals(session_key, raise_on_error=False):
    """
    Fetches gap/interval data between drivers.
    Available for race sessions only, updated approximately every 4 seconds.

    Args:
        session_key: Session identifier
        raise_on_error: If False, returns empty DataFrame when data unavailable

    Returns:
        DataFrame with columns: date, driver_number, gap_to_leader, interval,
                                session_key, meeting_key

    Note:
        Only available for race sessions, not practice or qualifying.
    """
    return fetch_data("intervals", {"session_key": session_key}, raise_on_error=raise_on_error)


#@st.cache_data
def fetch_weather(session_key, raise_on_error=False):
    """
    Fetches weather and track condition data.
    Updated approximately every minute.

    Args:
        session_key: Session identifier
        raise_on_error: If False, returns empty DataFrame when data unavailable

    Returns:
        DataFrame with columns: date, air_temperature, track_temperature,
                                humidity, pressure, rainfall, wind_speed,
                                wind_direction, session_key, meeting_key
    """
    return fetch_data("weather", {"session_key": session_key}, raise_on_error=raise_on_error)


#@st.cache_data
def fetch_race_control(session_key, raise_on_error=False):
    """
    Fetches race control messages including flags, safety cars, and penalties.

    Args:
        session_key: Session identifier
        raise_on_error: If False, returns empty DataFrame when data unavailable

    Returns:
        DataFrame with columns: date, category, message, flag, scope, sector,
                                lap_number, driver_number, session_key, meeting_key
    """
    return fetch_data("race_control", {"session_key": session_key}, raise_on_error=raise_on_error)


#@st.cache_data
def fetch_position(session_key, raise_on_error=False):
    """
    Fetches driver position data throughout the session.
    Higher granularity than lap-based position data.

    Args:
        session_key: Session identifier
        raise_on_error: If False, returns empty DataFrame when data unavailable

    Returns:
        DataFrame with columns: date, driver_number, position,
                                session_key, meeting_key
    """
    return fetch_data("position", {"session_key": session_key}, raise_on_error=raise_on_error)


#@st.cache_data
def fetch_location(session_key, driver_number=None, raise_on_error=False):
    """
    Fetches approximate car location on track in 3D coordinates.
    Sampled at approximately 3.7 Hz.

    Args:
        session_key: Session identifier
        driver_number: Optional driver number to filter
        raise_on_error: If False, returns empty DataFrame when data unavailable

    Returns:
        DataFrame with columns: date, driver_number, x, y, z,
                                session_key, meeting_key
    """
    params = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return fetch_data("location", params, raise_on_error=raise_on_error)