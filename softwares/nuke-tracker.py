import os, json, time, datetime, getpass, threading


class BaseTimeTracker:
    def __init__(self):
        self.IDLE_THRESHOLD = 180
        self.JSON_FILE = os.path.expanduser("~/activity_time_tracking.json")
        self.CHECK_INTERVAL = 5

        self.is_tracking = False
        self.current_session = None
        self.last_activity_time = None
        self.active_time = 0
        self.idle_time = 0
        self.running = True
        self.last_save_time = 0

        self.tracking_data = self.load_tracking_data()

        self.start_background_thread()
        print("Base Time Tracker initialized and running")

    def load_tracking_data(self):
        if os.path.exists(self.JSON_FILE):
            try:
                with open(self.JSON_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading tracking data: {e}")
                return []
        return []

    def save_tracking_data(self):
        try:
            with open(self.JSON_FILE, 'w') as f:
                json.dump(self.tracking_data, f, indent=4)
        except Exception as e:
            print(f"Error saving tracking data: {e}")

    def seconds_to_hh_mm_ss(self, seconds):
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def start_background_thread(self):
        self.thread = threading.Thread(target=self.activity_monitor_thread)
        self.thread.daemon = True
        self.thread.start()

    def activity_monitor_thread(self):
        while self.running:
            if self.is_tracking:
                self.check_activity()
            time.sleep(self.CHECK_INTERVAL)

    def start_tracking_session(self, app_name, start_file):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        username = getpass.getuser()

        if self.is_tracking:
            self.end_tracking_session()

        matching_session = None
        for session in reversed(self.tracking_data):
            if (session["log_date"] == today and
                session["username"] == username and
                session["application"] == app_name and
                session["start_file"] == start_file):
                matching_session = session
                break

        if matching_session:
            self.current_session = matching_session
            active_parts = matching_session["active_time"].split(":")
            idle_parts = matching_session["idle_time"].split(":")
            self.active_time = int(active_parts[0]) * 3600 + int(active_parts[1]) * 60 + int(active_parts[2])
            self.idle_time = int(idle_parts[0]) * 3600 + int(idle_parts[1]) * 60 + int(idle_parts[2])
            print(f"Continuing tracking session for {start_file}")
        else:
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
            print(f"Started new tracking session for {start_file}")

        self.is_tracking = True
        self.last_activity_time = time.time()
        self.last_save_time = time.time()

    def end_tracking_session(self):
        if not self.is_tracking or self.current_session is None:
            return

        self.check_activity()

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_session["end_time"] = now
        self.current_session["active_time"] = self.seconds_to_hh_mm_ss(self.active_time)
        self.current_session["idle_time"] = self.seconds_to_hh_mm_ss(self.idle_time)
        self.current_session["total_time"] = self.seconds_to_hh_mm_ss(self.active_time + self.idle_time)

        self.save_tracking_data()
        print(f"Ended session. Active: {self.current_session['active_time']}, Idle: {self.current_session['idle_time']}")

        self.is_tracking = False
        self.current_session = None

    def check_activity(self):
        if not self.is_tracking:
            return

        current_time = time.time()
        is_idle = (current_time - self.last_activity_time) > self.IDLE_THRESHOLD

        if is_idle:
            self.idle_time += self.CHECK_INTERVAL
        else:
            self.active_time += self.CHECK_INTERVAL

        if self.current_session:
            self.current_session["active_time"] = self.seconds_to_hh_mm_ss(self.active_time)
            self.current_session["idle_time"] = self.seconds_to_hh_mm_ss(self.idle_time)
            self.current_session["total_time"] = self.seconds_to_hh_mm_ss(self.active_time + self.idle_time)

            # Update end_time and ensure file tracking is consistent
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.current_session["end_time"] = now_str

            try:
                file_path = self.nuke.root().name()
                current_file = os.path.basename(file_path) if file_path else "untitled"

                if not self.current_session["start_file"] or self.current_session["start_file"] == "untitled":
                    self.current_session["start_file"] = current_file

                self.current_session["end_file"] = current_file

            except Exception as e:
                print(f"Could not update file info: {e}")

            if current_time - self.last_save_time >= 5:
                self.save_tracking_data()
                self.last_save_time = current_time

    def shutdown(self):
        self.running = False
        self.end_tracking_session()
        print("Tracker shut down")


class NukeTimeTracker(BaseTimeTracker):
    def __init__(self):
        self.JSON_FILE = os.path.expanduser("~/nuke_time_tracking.json")

        try:
            import nuke
            self.nuke = nuke
        except ImportError:
            print("RUN IN NUKE")
            return

        super(NukeTimeTracker, self).__init__()
        self.initialize_tracking()
        print("Nuke Time Tracker initialized")

    def initialize_tracking(self):
        try:
            file_path = self.nuke.root().name()
            file_name = os.path.basename(file_path) if file_path else "untitled"
            nuke_version = self.nuke.NUKE_VERSION_STRING
            app_name = f"Nuke {nuke_version}"
            self.start_tracking_session(app_name, file_name)
        except Exception as e:
            print(f"Error initializing tracking: {e}")


nuke_tracker = None


def initialize_nuke_tracker():
    global nuke_tracker
    if nuke_tracker is None:
        nuke_tracker = NukeTimeTracker()
    return nuke_tracker


if __name__ == "__main__":
    initialize_nuke_tracker()
