import os
import time
import datetime
import getpass
import json
from pathlib import Path
import atexit
from pynput import mouse, keyboard
import tempfile
import threading

# Get user and software info
USERNAME = getpass.getuser()
SOFTWARE_NAME = "Maya_2024"
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")

# Temp directory for JSON storage
temp_dir = "C:/temp"
json_path = os.path.join(temp_dir, f"software_{TODAY}.json")


def format_time_hms(seconds):
    """Convert seconds to readable hours:minutes:seconds format"""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def load_json():
    if os.path.exists(json_path):
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                # Convert stored times to formatted strings if they're numbers
                for key in ['active_time', 'idle_time', 'total_time']:
                    if key in data and isinstance(data[key], (int, float)):
                        data[key] = format_time_hms(int(data[key]))
                return data
        except json.JSONDecodeError:
            # Handle corrupted JSON file
            pass

    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    return {
        "username": USERNAME,
        "software": SOFTWARE_NAME,
        "date": TODAY,
        "start_time": current_time,
        "active_time": "00:00:00",
        "idle_time": "00:00:00",
        "total_time": "00:00:00",
        "_raw_active_seconds": 0,
        "_raw_idle_seconds": 0,
        "_raw_total_seconds": 0
    }


def save_json():
    # Create a copy of the data for saving
    save_data = usage_data.copy()

    # Store the raw seconds values for internal use
    save_data["_raw_active_seconds"] = raw_active_seconds
    save_data["_raw_idle_seconds"] = raw_idle_seconds
    save_data["_raw_total_seconds"] = raw_total_seconds

    with open(json_path, "w") as f:
        json.dump(save_data, f, indent=2)


# Load existing data or create new entry
usage_data = load_json()
start_time = time.time()

# Initialize raw seconds counters
raw_active_seconds = usage_data.get("_raw_active_seconds", 0)
raw_idle_seconds = usage_data.get("_raw_idle_seconds", 0)
raw_total_seconds = usage_data.get("_raw_total_seconds", 0)

last_activity = time.time()
IDLE_THRESHOLD = 300  # 5 minutes in seconds


# Define callback functions
def on_move(x, y):
    global last_activity
    last_activity = time.time()


def on_click(x, y, button, pressed):
    global last_activity
    last_activity = time.time()


def on_scroll(x, y, dx, dy):
    global last_activity
    last_activity = time.time()


def on_press(key):
    global last_activity
    last_activity = time.time()


# Final save function for when program exits
def final_save():
    global raw_total_seconds, raw_active_seconds, raw_idle_seconds

    current_time = time.time()
    raw_total_seconds = int(current_time - start_time)

    usage_data["total_time"] = format_time_hms(raw_total_seconds)
    usage_data["active_time"] = format_time_hms(raw_active_seconds)
    usage_data["idle_time"] = format_time_hms(raw_idle_seconds)
    usage_data["end_time"] = datetime.datetime.now().strftime('%H:%M:%S')

    save_json()
    print(f"Usage data saved to {json_path}")
    print(f"Total time: {usage_data['total_time']}")
    print(f"Active time: {usage_data['active_time']}")
    print(f"Idle time: {usage_data['idle_time']}")


# Register the final save function for program exit
atexit.register(final_save)


# Main tracking function that runs in a separate thread
def track_usage():
    global usage_data, TODAY, json_path, start_time
    global raw_active_seconds, raw_idle_seconds, raw_total_seconds

    try:
        last_check_time = time.time()

        while True:
            current_time = time.time()
            time_since_last_check = current_time - last_check_time
            elapsed_since_activity = current_time - last_activity

            if elapsed_since_activity > IDLE_THRESHOLD:
                raw_idle_seconds += time_since_last_check
            else:
                raw_active_seconds += time_since_last_check

            raw_total_seconds = int(current_time - start_time)

            # Update the formatted time strings
            usage_data["active_time"] = format_time_hms(int(raw_active_seconds))
            usage_data["idle_time"] = format_time_hms(int(raw_idle_seconds))
            usage_data["total_time"] = format_time_hms(raw_total_seconds)

            save_json()
            last_check_time = current_time

            # Check if date has changed
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            if current_date != TODAY:
                # Save final data for the day
                final_save()

                # Update date and create new file for the new day
                TODAY = current_date
                json_path = temp_dir / f"software_usage_{TODAY}.json"
                usage_data = load_json()
                start_time = time.time()
                raw_active_seconds = 0
                raw_idle_seconds = 0
                raw_total_seconds = 0

            time.sleep(1)

    except Exception as e:
        print(f"Error in usage tracking: {e}")
        final_save()


# Start listeners correctly with callbacks
mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
keyboard_listener = keyboard.Listener(on_press=on_press)
mouse_listener.start()
keyboard_listener.start()

# Start tracking in a background thread
tracking_thread = threading.Thread(target=track_usage, daemon=True)
tracking_thread.start()

print(f"Usage tracking started for {SOFTWARE_NAME}. Data will be saved to {json_path}")
print(f"Current active time: {usage_data['active_time']}")