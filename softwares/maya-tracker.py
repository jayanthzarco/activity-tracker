import maya.cmds as cmds
import maya.OpenMaya as om
import os
import json
import time
import datetime
import getpass
import threading


class MayaTimeTracker:
    def __init__(self):
        # Constants
        self.IDLE_THRESHOLD = 60  # seconds without activity considered idle
        self.JSON_FILE = os.path.expanduser("~/maya_time_tracking.json")
        self.CHECK_INTERVAL = 5  # seconds between activity checks

        # State variables
        self.is_tracking = False
        self.current_session = None
        self.last_activity_time = None
        self.active_time = 0
        self.idle_time = 0
        self.timer_callback_id = None
        self.running = True

        # Load existing data
        self.tracking_data = self.load_tracking_data()

        # Setup Maya callbacks
        self.setup_script_job()

        # Start the background thread
        self.start_background_thread()

        print("Maya Time Tracker initialized and running in background")

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

    def setup_script_job(self):
        """Set up Maya script jobs to track file operations"""
        # File open callback
        cmds.scriptJob(event=["SceneOpened", self.on_file_open])

        # New scene callback
        cmds.scriptJob(event=["NewSceneOpened", self.on_new_scene])

        # File save callback
        cmds.scriptJob(event=["SceneSaved", self.on_file_save])

        # Before scene save callback (to capture final file name)
        cmds.scriptJob(event=["BeforeSave", self.before_file_save])

        # Maya exit callback
        cmds.scriptJob(event=["quitApplication", self.on_maya_exit])

    def start_background_thread(self):
        """Start a background daemon thread for activity monitoring"""
        self.thread = threading.Thread(target=self.activity_monitor_thread)
        self.thread.daemon = True  # Set as daemon so it terminates when Maya exits
        self.thread.start()

    def activity_monitor_thread(self):
        """Background thread to monitor activity"""
        while self.running:
            if self.is_tracking:
                self.check_activity()
            time.sleep(self.CHECK_INTERVAL)

    def on_file_open(self):
        """Called when a file is opened"""
        file_path = cmds.file(q=True, sn=True)
        if file_path:
            file_name = os.path.basename(file_path)
            self.start_tracking_session(file_name)

    def on_new_scene(self):
        """Called when a new scene is created"""
        self.start_tracking_session("untitled")

    def before_file_save(self):
        """Called before a file is saved"""
        # Just to capture the fact we're about to save
        if self.is_tracking:
            self.check_activity()  # Update activity times

    def on_file_save(self):
        """Called when a file is saved"""
        file_path = cmds.file(q=True, sn=True)
        file_name = os.path.basename(file_path) if file_path else "untitled"

        if self.current_session:
            self.current_session["end_file"] = file_name
            self.save_tracking_data()
            print(f"TimeTracker: Updated session for {file_name}")

    def on_maya_exit(self):
        """Called when Maya is about to exit"""
        self.running = False
        self.end_tracking_session()

    def start_tracking_session(self, start_file):
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
            maya_version = cmds.about(version=True)
            current_time = datetime.datetime.now()
            time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

            self.current_session = {
                "username": username,
                "log_date": today,
                "software": f"maya {maya_version}",
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
        self.last_activity_time = current_time

        # Check for active Maya operations to determine if user was active
        # In a production environment, you might use more sophisticated activity detection
        # such as checking for changes in scene, or mouse/keyboard input
        is_active = False
        try:
            # Simple check: if Maya is responsive and not in idle state
            is_active = not cmds.about(batch=True)
        except:
            is_active = True  # Default to active if we can't determine

        # Determine if user was active or idle
        if not is_active or elapsed > self.IDLE_THRESHOLD:
            self.idle_time += elapsed
        else:
            self.active_time += elapsed

        # Update the current session
        if self.current_session:
            self.current_session["active_time"] = int(self.active_time)
            self.current_session["idle_time"] = int(self.idle_time)
            self.current_session["total_time"] = int(self.active_time + self.idle_time)

            # Update end time
            current_datetime = datetime.datetime.now()
            time_str = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
            self.current_session["end_time"] = time_str


# Global instance
time_tracker = None


def initialize_tracker():
    """Initialize the tracker singleton"""
    global time_tracker
    if time_tracker is None:
        time_tracker = MayaTimeTracker()
    return time_tracker


# Auto-initialize when imported
initialize_tracker()