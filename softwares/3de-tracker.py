#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 3D Equalizer Time Tracker - Python 2.7.5 Compatible Version

import os, json, time, datetime, getpass, threading


# Try to import pynput - if not available, provide instructions
try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Continuing with limited functionality (no automatic idle detection).")


class BaseTimeTracker(object):
    def __init__(self):
        # Constants
        self.IDLE_THRESHOLD = 180  # seconds without activity considered idle
        self.JSON_FILE = os.path.expanduser("~/activity_time_tracking.json")
        self.CHECK_INTERVAL = 5  # seconds between activity checks

        # State variables
        self.is_tracking = False
        self.current_session = None
        self.last_activity_time = None
        self.active_time = 0
        self.idle_time = 0
        self.running = True
        self.user_active = False
        self.last_save_time = 0

        # Load existing data
        self.tracking_data = self.load_tracking_data()

        # Setup input listeners if pynput is available
        if PYNPUT_AVAILABLE:
            self.setup_input_listeners()
        else:
            # Set initial activity time
            self.last_activity_time = time.time()

        # Start the background thread
        self.start_background_thread()

        print("Base Time Tracker initialized and running in background")

    def load_tracking_data(self):
        """Load existing tracking data from JSON file"""
        if os.path.exists(self.JSON_FILE):
            try:
                with open(self.JSON_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print("TimeTracker: Error loading tracking data: {0}".format(e))
                return []
        return []

    def save_tracking_data(self):
        """Save tracking data to JSON file"""
        try:
            with open(self.JSON_FILE, 'w') as f:
                json.dump(self.tracking_data, f, indent=4)
        except Exception as e:
            print("TimeTracker: Error saving tracking data: {0}".format(e))

    def setup_input_listeners(self):
        """Set up listeners for mouse and keyboard activity"""
        if not PYNPUT_AVAILABLE:
            return

        # Create and start mouse listener
        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll
        )
        self.mouse_listener.daemon = True
        self.mouse_listener.start()

        # Create and start keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()

    def on_mouse_move(self, x, y):
        """Callback for mouse movement"""
        self.user_active = True
        self.last_activity_time = time.time()

    def on_mouse_click(self, x, y, button, pressed):
        """Callback for mouse clicks"""
        self.user_active = True
        self.last_activity_time = time.time()

    def on_mouse_scroll(self, x, y, dx, dy):
        """Callback for mouse scrolling"""
        self.user_active = True
        self.last_activity_time = time.time()

    def on_key_press(self, key):
        """Callback for keyboard press"""
        self.user_active = True
        self.last_activity_time = time.time()

    def on_key_release(self, key):
        """Callback for keyboard release"""
        self.user_active = True
        self.last_activity_time = time.time()

    def seconds_to_hh_mm_ss(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)

    def start_background_thread(self):
        """Start a background daemon thread for activity monitoring"""
        self.thread = threading.Thread(target=self.activity_monitor_thread)
        self.thread.daemon = True  # Set as daemon so it terminates when main application exits
        self.thread.start()

    def activity_monitor_thread(self):
        """Background thread to monitor activity"""
        while self.running:
            if self.is_tracking:
                self.check_activity()
            time.sleep(self.CHECK_INTERVAL)

    def start_tracking_session(self, app_name, start_file):
        """Start a new tracking session"""
        # Check if we already have a session for today with the same file
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        username = getpass.getuser()

        # If we already have an active session, end it first
        if self.is_tracking:
            self.end_tracking_session()

        # Look for an existing session from today with the same start file
        matching_session = None
        for session in reversed(self.tracking_data):
            if (session["log_date"] == today and
                    session["username"] == username and
                    session["application"] == app_name and
                    session["start_file"] == start_file):
                matching_session = session
                break

        if matching_session:
            # Continue the existing session
            self.current_session = matching_session
            # Parse the time format back to seconds for internal tracking
            active_parts = matching_session["active_time"].split(":")
            idle_parts = matching_session["idle_time"].split(":")

            self.active_time = int(active_parts[0]) * 3600 + int(active_parts[1]) * 60 + int(active_parts[2])
            self.idle_time = int(idle_parts[0]) * 3600 + int(idle_parts[1]) * 60 + int(idle_parts[2])

            print("TimeTracker: Continuing tracking session for {0}".format(start_file))
        else:
            # Create a new session
            current_time = datetime.datetime.now()
            time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

            self.current_session = {
                "username": username,
                "log_date": today,
                "application": app_name,
                "start_file": start_file,
                "end_file": start_file,  # Initially same as start
                "start_time": time_str,
                "active_time": "00:00:00",
                "idle_time": "00:00:00",
                "total_time": "00:00:00",
                "end_time": time_str  # Will be updated
            }

            self.tracking_data.append(self.current_session)
            self.active_time = 0
            self.idle_time = 0
            print("TimeTracker: Started tracking session for {0}".format(start_file))

        self.is_tracking = True
        self.last_activity_time = time.time()
        self.last_save_time = time.time()
        self.user_active = True  # Start by assuming user is active

    def end_tracking_session(self):
        """End the current tracking session"""
        if not self.is_tracking or self.current_session is None:
            return

        # Update activity times one last time
        self.check_activity()

        # Update session with final times
        current_time = datetime.datetime.now()
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

        self.current_session["end_time"] = time_str
        self.current_session["active_time"] = self.seconds_to_hh_mm_ss(self.active_time)
        self.current_session["idle_time"] = self.seconds_to_hh_mm_ss(self.idle_time)
        self.current_session["total_time"] = self.seconds_to_hh_mm_ss(self.active_time + self.idle_time)

        self.save_tracking_data()

        print(
            "TimeTracker: Ended tracking session. Active: {0}, Idle: {1}".format(
                self.seconds_to_hh_mm_ss(self.active_time),
                self.seconds_to_hh_mm_ss(self.idle_time)
            )
        )

        # Reset state
        self.is_tracking = False
        self.current_session = None

    def check_activity(self):
        """Check for user activity and update time counters"""
        if not self.is_tracking:
            return

        current_time = time.time()

        # If pynput is not available, assume user is always active or handle manually
        if not PYNPUT_AVAILABLE:
            # Register activity every time 3DE calls a tool or function
            # This is a fallback that will be improved in the TDETimeTracker class
            self.active_time += self.CHECK_INTERVAL
        else:
            # Determine if user is idle based on time since last input
            is_idle = (current_time - self.last_activity_time) > self.IDLE_THRESHOLD

            if is_idle:
                # User is idle
                self.idle_time += self.CHECK_INTERVAL
                self.user_active = False
            else:
                # User is active
                self.active_time += self.CHECK_INTERVAL

        # Update the current session
        if self.current_session:
            self.current_session["active_time"] = self.seconds_to_hh_mm_ss(self.active_time)
            self.current_session["idle_time"] = self.seconds_to_hh_mm_ss(self.idle_time)
            self.current_session["total_time"] = self.seconds_to_hh_mm_ss(self.active_time + self.idle_time)

            # Update end time
            current_datetime = datetime.datetime.now()
            time_str = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
            self.current_session["end_time"] = time_str

            # Save to JSON every 5 seconds
            if current_time - self.last_save_time >= 5:
                self.save_tracking_data()
                self.last_save_time = current_time

    def shutdown(self):
        """Clean shutdown of tracker"""
        self.running = False
        # Stop input listeners
        if PYNPUT_AVAILABLE:
            if hasattr(self, 'mouse_listener') and self.mouse_listener.is_alive():
                self.mouse_listener.stop()
            if hasattr(self, 'keyboard_listener') and self.keyboard_listener.is_alive():
                self.keyboard_listener.stop()
        self.end_tracking_session()
        print("Time Tracker shut down")

    def manual_activity_ping(self):
        """Method that can be called from 3DE callbacks to register activity"""
        self.last_activity_time = time.time()
        self.user_active = True


class TDETimeTracker(BaseTimeTracker):
    def __init__(self):
        # Define 3DEqualizer-specific constants
        self.JSON_FILE = os.path.expanduser("~/3de_time_tracking.json")

        # Import 3DEqualizer modules here to avoid issues if used in non-3DE environment
        try:
            import tde4
            self.tde4 = tde4
            self.tde_available = True
        except ImportError:
            print("WARNING: Unable to import tde4 module. Run this script in 3D Equalizer.")
            self.tde_available = False

        # Call parent constructor - use old-style class call for Python 2.7
        BaseTimeTracker.__init__(self)

        # Initialize tracking if a project is already open
        if self.tde_available:
            self.initialize_tracking()
            print("3D Equalizer Time Tracker initialized")
        else:
            print("Running in limited mode without 3DE API access")

    def get_3de_version(self):
        """Get 3DEqualizer version safely"""
        if not self.tde_available:
            return "Unknown"

        try:
            # Different 3DE versions might have different ways to get version info
            # Try standard method first
            version = self.tde4.get3DEVersion()
            if version:
                return version

            # Alternative methods if the above doesn't work
            try:
                release = self.tde4.get3DERelease()
                if release:
                    return release
            except:
                pass

            # If all fails, return a default
            return "Unknown"
        except:
            return "Unknown"

    def get_project_path(self):
        """Get current project path safely"""
        if not self.tde_available:
            return ""

        try:
            # Different 3DE versions might have different API calls
            # Try the most common ones
            try:
                return self.tde4.getProjectPath()
            except:
                pass

            try:
                return self.tde4.getProjectFilepath()
            except:
                pass

            # If all else fails
            return ""
        except:
            return ""

    def initialize_tracking(self):
        """Initialize tracking based on current 3DEqualizer state"""
        try:
            # Get current project path
            project_path = self.get_project_path()
            project_name = os.path.basename(project_path) if project_path else "untitled"

            # Get 3DE version
            version = self.get_3de_version()
            app_name = "3DEqualizer {0}".format(version)

            self.start_tracking_session(app_name, project_name)
        except Exception as e:
            print("TimeTracker: Error initializing tracking: {0}".format(e))

    def check_activity(self):
        """Override check_activity to update file information only"""
        # First, run the parent class's check_activity
        BaseTimeTracker.check_activity(self)

        # Then, update file information if in 3DE
        if self.tde_available:
            try:
                if self.is_tracking and self.current_session:
                    project_path = self.get_project_path()
                    current_file = os.path.basename(project_path) if project_path else "untitled"

                    # If no start file is set, use current file as start file
                    if not self.current_session["start_file"] or self.current_session["start_file"] == "untitled":
                        if current_file != "untitled":
                            self.current_session["start_file"] = current_file

                    # Always update end file to current file
                    self.current_session["end_file"] = current_file

            except Exception as e:
                print("TimeTracker: Error updating file information: {0}".format(e))

    def record_action(self, action_name):
        """Record a specific 3DE user action - simplified to just ping activity"""
        if not self.is_tracking:
            return

        # Register that the user is active
        self.manual_activity_ping()

    def on_project_close(self):
        """Called when 3DEqualizer project is closed or 3DE is exiting"""
        self.shutdown()


# Global singleton instance
tde_tracker = None


def initialize_tde_tracker():
    """Initialize the 3DEqualizer tracker singleton"""
    global tde_tracker
    if tde_tracker is None:
        tde_tracker = TDETimeTracker()
    return tde_tracker


# def record_user_action(action_name):
#     """Helper function to record a user action from 3DE scripts"""
#     global tde_tracker
#     if tde_tracker is not None:
#         tde_tracker.record_action(action_name)
#     else:
#         tde_tracker = initialize_tde_tracker()
#         tde_tracker.record_action(action_name)


# Auto-initialize when imported in 3DEqualizer
if __name__ == "__main__":
    initialize_tde_tracker()