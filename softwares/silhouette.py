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


class SilhouetteTimeTracker(BaseTimeTracker):
    def __init__(self):
        # Define Silhouette-specific constants
        self.JSON_FILE = os.path.expanduser("~/silhouette_time_tracking.json")

        # Call parent constructor
        super(SilhouetteTimeTracker, self).__init__()

        # Import Silhouette modules here to avoid issues if used in non-Silhouette environment
        try:
            import fx
        except ImportError:
            print("RUN IN SILHOUETTE FX")
            return
        self.fx = fx

        # Setup Silhouette callbacks/monitoring
        self.setup_monitoring()

        print("Silhouette FX Time Tracker initialized")

    def setup_monitoring(self):
        """Set up Silhouette monitoring to track file operations"""
        try:
            # Silhouette Python API usage depends on the version
            # The approach below uses both a polling method and attempts to use callbacks if available

            # Start file monitoring thread
            self.start_file_monitoring()

            # Try to set up signal/event handlers if available in this Silhouette version
            self.setup_event_handlers()

        except Exception as e:
            print(f"TimeTracker: Error setting up Silhouette monitoring: {e}")

    def start_file_monitoring(self):
        """Start a thread to monitor file changes in Silhouette"""

        def monitor_silhouette_files():
            last_project_path = ""

            while self.running:
                try:
                    # Get current project file
                    current_path = self.get_current_project_path()

                    # Check if project file changed
                    if current_path != last_project_path:
                        if current_path:
                            # New project loaded or saved
                            file_name = os.path.basename(current_path)
                            self.start_silhouette_session(file_name)
                        else:
                            # Project may have been closed
                            self.end_tracking_session()

                        last_project_path = current_path

                except Exception as e:
                    print(f"TimeTracker: Error monitoring Silhouette files: {e}")

                # Check every few seconds
                time.sleep(5)

        # Start the monitoring thread
        monitor_thread = threading.Thread(target=monitor_silhouette_files)
        monitor_thread.daemon = True
        monitor_thread.start()

    def setup_event_handlers(self):
        """Set up event handlers for Silhouette if available"""
        try:
            # Silhouette has different script interfaces in different versions
            # Try to attach to events if they exist

            # Method 1: Try using script object if available (newer versions)
            if hasattr(self.fx, 'script'):
                # Connect to file open/save events if they exist
                if hasattr(self.fx.script, 'connect'):
                    # Example connection to events (adjust based on actual API)
                    self.fx.script.connect("projectOpened", self.on_project_opened)
                    self.fx.script.connect("projectSaved", self.on_project_saved)
                    self.fx.script.connect("projectClosed", self.on_project_closed)
                    self.fx.script.connect("applicationExit", self.on_application_exit)

            # Method 2: Try older API styles
            elif hasattr(self.fx, 'addCallback'):
                # Example for older API style
                self.fx.addCallback("open", self.on_project_opened)
                self.fx.addCallback("save", self.on_project_saved)
                self.fx.addCallback("close", self.on_project_closed)
                self.fx.addCallback("exit", self.on_application_exit)

        except Exception as e:
            print(f"TimeTracker: Could not set up Silhouette event handlers: {e}")
            print("Using polling method only")

    def get_current_project_path(self):
        """Get the path of the current project in Silhouette"""
        try:
            # Method 1: Try using project object if available
            if hasattr(self.fx, 'project'):
                return self.fx.project.path()

            # Method 2: Try alternative API
            elif hasattr(self.fx, 'getProjectPath'):
                return self.fx.getProjectPath()

            # Method 3: Another possible path getter
            elif hasattr(self.fx, 'getCurrentProject'):
                project = self.fx.getCurrentProject()
                if project:
                    return project.getPath()

            # No method worked
            return ""

        except Exception as e:
            print(f"TimeTracker: Error getting Silhouette project path: {e}")
            return ""

    def get_silhouette_version(self):
        """Get Silhouette version"""
        try:
            # Try different methods to get version
            if hasattr(self.fx, 'version'):
                return self.fx.version()
            elif hasattr(self.fx, 'getVersion'):
                return self.fx.getVersion()
            else:
                return "Unknown"
        except:
            return "Unknown"

    def on_project_opened(self, *args, **kwargs):
        """Called when a project is opened"""
        file_path = self.get_current_project_path()
        if file_path:
            file_name = os.path.basename(file_path)
            self.start_silhouette_session(file_name)

    def on_project_saved(self, *args, **kwargs):
        """Called when a project is saved"""
        file_path = self.get_current_project_path()
        file_name = os.path.basename(file_path) if file_path else "untitled"

        if self.current_session:
            self.current_session["end_file"] = file_name
            self.save_tracking_data()
            print(f"TimeTracker: Updated session for {file_name}")

    def on_project_closed(self, *args, **kwargs):
        """Called when a project is closed"""
        self.end_tracking_session()

    def on_application_exit(self, *args, **kwargs):
        """Called when Silhouette is exiting"""
        self.shutdown()

    def start_silhouette_session(self, file_name):
        """Start tracking for a Silhouette file"""
        silhouette_version = self.get_silhouette_version()
        app_name = f"Silhouette FX {silhouette_version}"
        self.start_tracking_session(app_name, file_name)


silhouette_tracker = None


def initialize_silhouette_tracker():
    """Initialize the Silhouette tracker singleton"""
    global silhouette_tracker
    if silhouette_tracker is None:
        silhouette_tracker = SilhouetteTimeTracker()
    return silhouette_tracker


# Auto-initialize when imported in Silhouette
if __name__ == "__main__":
    # In production, you would use:
    initialize_silhouette_tracker()