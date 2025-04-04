import os
import json
import time
import datetime
import getpass
import threading
from pynput import mouse, keyboard


class BaseTimeTracker:
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

        # Setup input listeners
        self.setup_input_listeners()

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
                print(f"TimeTracker: Error loading tracking data: {e}")
                return []
        return []

    def save_tracking_data(self):
        """Save tracking data to JSON file"""
        try:
            with open(self.JSON_FILE, 'w') as f:
                json.dump(self.tracking_data, f, indent=4)
        except Exception as e:
            print(f"TimeTracker: Error saving tracking data: {e}")

    def setup_input_listeners(self):
        """Set up listeners for mouse and keyboard activity"""
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
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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

            print(f"TimeTracker: Continuing tracking session for {start_file}")
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
            print(f"TimeTracker: Started tracking session for {start_file}")

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
            f"TimeTracker: Ended tracking session. Active: {self.seconds_to_hh_mm_ss(self.active_time)}, Idle: {self.seconds_to_hh_mm_ss(self.idle_time)}")

        # Reset state
        self.is_tracking = False
        self.current_session = None

    def check_activity(self):
        """Check for user activity and update time counters"""
        if not self.is_tracking:
            return

        current_time = time.time()

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
        if hasattr(self, 'mouse_listener') and self.mouse_listener.is_alive():
            self.mouse_listener.stop()
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener.is_alive():
            self.keyboard_listener.stop()
        self.end_tracking_session()
        print("Time Tracker shut down")


class TDETimeTracker(BaseTimeTracker):
    def __init__(self):
        # Define 3DEqualizer-specific constants
        self.JSON_FILE = os.path.expanduser("~/3de_time_tracking.json")

        # Call parent constructor
        super(TDETimeTracker, self).__init__()

        # Import 3DEqualizer modules here to avoid issues if used in non-3DE environment
        try:
            import tde4
        except ImportError:
            print("RUN IN 3DEQUALIZER")
            return
        self.tde4 = tde4

        # Setup 3DEqualizer callbacks
        self.setup_callbacks()

        print("3DEqualizer Time Tracker initialized")

    def setup_callbacks(self):
        """Set up 3DEqualizer callbacks to track file operations"""
        try:
            # Unfortunately 3DEqualizer doesn't have built-in callbacks like Maya or Nuke
            # We'll use a polling approach instead and hook into menu commands
            self.poll_current_file()

        except Exception as e:
            print(f"TimeTracker: Error setting up 3DEqualizer callbacks: {e}")

    def poll_current_file(self):
        """Start a polling thread to check for file changes in 3DEqualizer"""

        def poll_file_thread():
            last_project_path = ""
            while self.running:
                try:
                    # Check if project has changed
                    current_project_path = self.get_current_project_path()

                    if current_project_path != last_project_path:
                        # Project changed
                        if current_project_path:
                            # Project opened or changed
                            file_name = os.path.basename(current_project_path)
                            self.start_tde_session(file_name)
                        else:
                            # Project closed
                            self.end_tracking_session()

                        last_project_path = current_project_path

                except Exception as e:
                    print(f"TimeTracker: Error polling 3DEqualizer: {e}")

                time.sleep(5)  # Check every 5 seconds

        # Start polling thread
        poll_thread = threading.Thread(target=poll_file_thread)
        poll_thread.daemon = True
        poll_thread.start()

    def get_current_project_path(self):
        """Get current 3DEqualizer project path"""
        try:
            # Get current project path - this method will vary based on 3DE API
            project_path = self.tde4.getProjectPath()
            return project_path
        except:
            # Fallback method if the above doesn't work
            try:
                # Another possible way to get project path
                cam_list = self.tde4.getCameraList()
                if cam_list:
                    return self.tde4.getCameraPath(cam_list[0])
                return ""
            except:
                return ""

    def hook_3de_menu_callbacks(self):
        """
        Hook into 3DEqualizer menu commands to track file operations
        Note: This requires custom menu integration in 3DEqualizer
        """
        try:
            # This is a simplified example - actual implementation would depend on
            # how 3DEqualizer allows for menu customization

            # Example of how to hook file operations if 3DE supports it
            req = self.tde4.createCustomRequester()

            # Hook file open
            self.tde4.addMenuBarWidget(req, "File_Open_Menu", "File/Open...")
            self.tde4.setWidgetCallbackFunction(req, "File_Open_Menu", "on_file_open")

            # Hook file save
            self.tde4.addMenuBarWidget(req, "File_Save_Menu", "File/Save")
            self.tde4.setWidgetCallbackFunction(req, "File_Save_Menu", "on_file_save")

            # Hook file save as
            self.tde4.addMenuBarWidget(req, "File_SaveAs_Menu", "File/Save As...")
            self.tde4.setWidgetCallbackFunction(req, "File_SaveAs_Menu", "on_file_save_as")

            # Hook application exit
            self.tde4.addMenuBarWidget(req, "File_Exit_Menu", "File/Exit")
            self.tde4.setWidgetCallbackFunction(req, "File_Exit_Menu", "on_app_exit")

        except Exception as e:
            print(f"TimeTracker: Error setting up 3DEqualizer menu hooks: {e}")

    def on_file_open(self, req, widget, action):
        """Called when a file is opened"""
        file_path = self.get_current_project_path()
        if file_path:
            file_name = os.path.basename(file_path)
            self.start_tde_session(file_name)

    def on_file_save(self, req, widget, action):
        """Called when a file is saved"""
        file_path = self.get_current_project_path()
        if file_path and self.current_session:
            file_name = os.path.basename(file_path)
            self.current_session["end_file"] = file_name
            self.save_tracking_data()
            print(f"TimeTracker: Updated session for {file_name}")

    def on_file_save_as(self, req, widget, action):
        """Called when a file is saved as a new file"""
        file_path = self.get_current_project_path()
        if file_path and self.current_session:
            file_name = os.path.basename(file_path)
            self.current_session["end_file"] = file_name
            self.save_tracking_data()
            print(f"TimeTracker: Updated session for {file_name}")

    def on_app_exit(self, req, widget, action):
        """Called when 3DEqualizer is exiting"""
        self.shutdown()

    def start_tde_session(self, file_name):
        """Start tracking for a 3DEqualizer file"""
        try:
            # Get 3DEqualizer version
            tde_version = self.tde4.get3DEVersion()
        except:
            tde_version = "Unknown"

        app_name = f"3DEqualizer {tde_version}"
        self.start_tracking_session(app_name, file_name)


tde_tracker = None


def initialize_tde_tracker():
    """Initialize the 3DEqualizer tracker singleton"""
    global tde_tracker
    if tde_tracker is None:
        tde_tracker = TDETimeTracker()
    return tde_tracker


# Auto-initialize when imported in 3DEqualizer
if __name__ == "__main__":
    # In production, you would use:
    initialize_tde_tracker()