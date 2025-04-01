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
        self.IDLE_THRESHOLD = 60  # seconds without activity considered idle
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
            self.active_time = matching_session["active_time"]
            self.idle_time = matching_session["idle_time"]
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
                "active_time": 0,
                "idle_time": 0,
                "total_time": 0,
                "end_time": time_str  # Will be updated
            }

            self.tracking_data.append(self.current_session)
            self.active_time = 0
            self.idle_time = 0
            print(f"TimeTracker: Started tracking session for {start_file}")

        self.is_tracking = True
        self.last_activity_time = time.time()
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
        self.current_session["active_time"] = int(self.active_time)
        self.current_session["idle_time"] = int(self.idle_time)
        self.current_session["total_time"] = int(self.active_time + self.idle_time)

        self.save_tracking_data()

        print(f"TimeTracker: Ended tracking session. Active: {int(self.active_time)}s, Idle: {int(self.idle_time)}s")

        # Reset state
        self.is_tracking = False
        self.current_session = None

    def check_activity(self):
        """Check for user activity and update time counters"""
        if not self.is_tracking:
            return

        current_time = time.time()
        elapsed = current_time - self.last_activity_time

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
            self.current_session["active_time"] = int(self.active_time)
            self.current_session["idle_time"] = int(self.idle_time)
            self.current_session["total_time"] = int(self.active_time + self.idle_time)

            # Update end time
            current_datetime = datetime.datetime.now()
            time_str = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
            self.current_session["end_time"] = time_str

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


class MayaTimeTracker(BaseTimeTracker):
    def __init__(self):
        # Define Maya-specific constants
        self.JSON_FILE = os.path.expanduser("~/maya_time_tracking.json")

        # Call parent constructor
        super(MayaTimeTracker, self).__init__()

        # Import Maya modules here to avoid issues if used in non-Maya environment
        import maya.cmds as cmds
        self.cmds = cmds

        # Setup Maya callbacks
        self.setup_script_job()

        print("Maya Time Tracker initialized")

    def setup_script_job(self):
        """Set up Maya script jobs to track file operations"""
        # File open callback
        self.cmds.scriptJob(event=["SceneOpened", self.on_file_open])

        # New scene callback
        self.cmds.scriptJob(event=["NewSceneOpened", self.on_new_scene])

        # File save callback
        self.cmds.scriptJob(event=["SceneSaved", self.on_file_save])

        # Before scene save callback (to capture final file name)
        self.cmds.scriptJob(event=["BeforeSave", self.before_file_save])

        # Maya exit callback
        self.cmds.scriptJob(event=["quitApplication", self.on_maya_exit])

    def on_file_open(self):
        """Called when a file is opened"""
        file_path = self.cmds.file(q=True, sn=True)
        if file_path:
            file_name = os.path.basename(file_path)
            self.start_maya_session(file_name)

    def on_new_scene(self):
        """Called when a new scene is created"""
        self.start_maya_session("untitled")

    def before_file_save(self):
        """Called before a file is saved"""
        # Just to capture the fact we're about to save
        if self.is_tracking:
            self.check_activity()  # Update activity times

    def on_file_save(self):
        """Called when a file is saved"""
        file_path = self.cmds.file(q=True, sn=True)
        file_name = os.path.basename(file_path) if file_path else "untitled"

        if self.current_session:
            self.current_session["end_file"] = file_name
            self.save_tracking_data()
            print(f"TimeTracker: Updated session for {file_name}")

    def on_maya_exit(self):
        """Called when Maya is about to exit"""
        self.shutdown()

    def start_maya_session(self, file_name):
        """Start tracking for a Maya file"""
        maya_version = self.cmds.about(version=True)
        app_name = f"Maya {maya_version}"
        self.start_tracking_session(app_name, file_name)


class BlenderTimeTracker(BaseTimeTracker):
    """Example implementation for Blender"""

    def __init__(self):
        # Define Blender-specific constants
        self.JSON_FILE = os.path.expanduser("~/blender_time_tracking.json")

        # Call parent constructor
        super(BlenderTimeTracker, self).__init__()

        # Import Blender modules (would be done here)
        # import bpy
        # self.bpy = bpy

        # Setup Blender callbacks - this would be implementation-specific
        # self.setup_blender_handlers()

        print("Blender Time Tracker initialized - EXAMPLE ONLY")

    # Additional Blender-specific methods would be implemented here


# Global instance for Maya
maya_tracker = None


def initialize_maya_tracker():
    """Initialize the Maya tracker singleton"""
    global maya_tracker
    if maya_tracker is None:
        maya_tracker = MayaTimeTracker()
    return maya_tracker


# Function to instantiate tracker for any other application
def create_tracker_for_application(app_name, json_file_path=None):
    """Create a custom tracker for any application"""
    tracker = BaseTimeTracker()
    if json_file_path:
        tracker.JSON_FILE = json_file_path
    print(f"Created time tracker for {app_name}")
    return tracker


# Auto-initialize when imported in Maya
if __name__ == "__main__":
    # This would be the entry point when running as a script
    # For testing, you could create a simple tracker
    test_tracker = create_tracker_for_application("TestApp")
    test_tracker.start_tracking_session("TestApp", "test_file.txt")

    # In production, you would use:
    # initialize_maya_tracker()