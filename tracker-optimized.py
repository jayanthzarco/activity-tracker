import os
import json
import time
import threading
import datetime
import getpass
from pynput import mouse, keyboard


class OptimizedTimeTracker:
    def __init__(self):
        # Optimize constants
        self.IDLE_THRESHOLD = 180  # seconds
        self.JSON_FILE = os.path.expanduser("~/activity_time_tracking.json")
        self.CHECK_INTERVAL = 10  # Increased to reduce CPU usage
        self.SAVE_INTERVAL = 30  # Save less frequently (every 30 seconds)

        # State variables
        self.is_tracking = False
        self.current_session = None
        self.last_activity_time = None
        self.active_time = 0
        self.idle_time = 0
        self.running = True
        self.user_active = False
        self.last_save_time = 0
        self.pending_activity = False  # Flag for activity without immediate processing

        # Use a lock for thread safety
        self.lock = threading.Lock()

        # Load data only when needed
        self.tracking_data = []

        # Setup lightweight event handling
        self.setup_input_listeners()

        # Start monitoring thread
        self.start_background_thread()

        print("Optimized Time Tracker initialized")

    def load_tracking_data(self):
        """Load data only when needed"""
        if not self.tracking_data and os.path.exists(self.JSON_FILE):
            try:
                with open(self.JSON_FILE, 'r') as f:
                    self.tracking_data = json.load(f)
            except Exception as e:
                print(f"Error loading data: {e}")
                self.tracking_data = []
        return self.tracking_data

    def save_tracking_data(self):
        """Save data with less frequency"""
        try:
            with open(self.JSON_FILE, 'w') as f:
                json.dump(self.tracking_data, f)  # Removed indent for efficiency
        except Exception as e:
            print(f"Error saving data: {e}")

    def setup_input_listeners(self):
        """Optimized input listeners with debouncing"""
        # Simplified mouse listener - only track essential events
        self.mouse_listener = mouse.Listener(
            on_click=self.on_activity,  # Only listen for clicks
            on_scroll=self.on_activity  # And scrolls
        )
        self.mouse_listener.daemon = True
        self.mouse_listener.start()

        # Simplified keyboard listener
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_activity  # Only track key presses
        )
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()

    def on_activity(self, *args, **kwargs):
        """Simplified activity handler to reduce processing"""
        # Just set a flag instead of processing immediately
        self.pending_activity = True

    @staticmethod
    def seconds_to_hh_mm_ss(seconds):
        """Convert seconds to HH:MM:SS format"""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def start_background_thread(self):
        """Start monitoring thread with lower priority"""
        self.thread = threading.Thread(target=self.activity_monitor_thread)
        self.thread.daemon = True
        self.thread.start()

    def activity_monitor_thread(self):
        """Optimized monitoring thread"""
        while self.running:
            # Process pending activity flag
            if self.pending_activity:
                with self.lock:
                    self.last_activity_time = time.time()
                    self.user_active = True
                    self.pending_activity = False

            # Only process if we're tracking
            if self.is_tracking:
                self.check_activity()

                # Save data periodically instead of every check
                current_time = time.time()
                if current_time - self.last_save_time >= self.SAVE_INTERVAL:
                    self.save_tracking_data()
                    self.last_save_time = current_time

            time.sleep(self.CHECK_INTERVAL)

    def start_tracking_session(self, app_name, start_file):
        """Start tracking with data loading on demand"""
        with self.lock:
            # Load data if not already loaded
            self.load_tracking_data()

            # End any current session
            if self.is_tracking:
                self.end_tracking_session()

            today = datetime.datetime.now().strftime("%Y-%m-%d")
            username = getpass.getuser()

            # Find existing session
            matching_session = None
            for session in reversed(self.tracking_data):
                if (session.get("log_date") == today and
                        session.get("username") == username and
                        session.get("application") == app_name and
                        session.get("start_file") == start_file):
                    matching_session = session
                    break

            if matching_session:
                # Continue existing session
                self.current_session = matching_session
                active_parts = matching_session["active_time"].split(":")
                idle_parts = matching_session["idle_time"].split(":")
                self.active_time = int(active_parts[0]) * 3600 + int(active_parts[1]) * 60 + int(active_parts[2])
                self.idle_time = int(idle_parts[0]) * 3600 + int(idle_parts[1]) * 60 + int(idle_parts[2])
            else:
                # Create new session with minimal data
                current_time = datetime.datetime.now()
                time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

                self.current_session = {
                    "username": username,
                    "log_date": today,
                    "application": app_name,
                    "start_file": start_file,
                    "end_file": start_file,
                    "start_time": time_str,
                    "active_time": "00:00:00",
                    "idle_time": "00:00:00",
                    "total_time": "00:00:00",
                    "end_time": time_str
                }

                self.tracking_data.append(self.current_session)
                self.active_time = 0
                self.idle_time = 0

            self.is_tracking = True
            self.last_activity_time = time.time()
            self.last_save_time = time.time()
            self.user_active = True

            print(f"Tracking started for {start_file}")

    def end_tracking_session(self):
        """End current session with clean shutdown"""
        with self.lock:
            if not self.is_tracking or self.current_session is None:
                return

            self.check_activity()

            current_time = datetime.datetime.now()
            time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")

            self.current_session["end_time"] = time_str
            self.current_session["active_time"] = self.seconds_to_hh_mm_ss(self.active_time)
            self.current_session["idle_time"] = self.seconds_to_hh_mm_ss(self.idle_time)
            self.current_session["total_time"] = self.seconds_to_hh_mm_ss(self.active_time + self.idle_time)

            # Save data immediately on session end
            self.save_tracking_data()

            print(f"Tracking ended. Active: {self.seconds_to_hh_mm_ss(self.active_time)}")

            self.is_tracking = False
            self.current_session = None

    def check_activity(self):
        """Efficient activity check"""
        if not self.is_tracking:
            return

        current_time = time.time()

        # Check for idle state
        is_idle = (current_time - self.last_activity_time) > self.IDLE_THRESHOLD

        if is_idle:
            # Only count idle if previously active
            if self.user_active:
                self.user_active = False
            self.idle_time += self.CHECK_INTERVAL
        else:
            self.active_time += self.CHECK_INTERVAL

        # Update session time strings only when needed for display or saving
        if self.current_session and (current_time - self.last_save_time >= self.SAVE_INTERVAL):
            self.current_session["active_time"] = self.seconds_to_hh_mm_ss(self.active_time)
            self.current_session["idle_time"] = self.seconds_to_hh_mm_ss(self.idle_time)
            self.current_session["total_time"] = self.seconds_to_hh_mm_ss(self.active_time + self.idle_time)
            self.current_session["end_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def shutdown(self):
        """Clean shutdown"""
        with self.lock:
            self.running = False
            if hasattr(self, 'mouse_listener'):
                self.mouse_listener.stop()
            if hasattr(self, 'keyboard_listener'):
                self.keyboard_listener.stop()
            self.end_tracking_session()
            print("Time Tracker shut down")


cv = OptimizedTimeTracker()
t = cv.seconds_to_hh_mm_ss(3335555)
print(t)