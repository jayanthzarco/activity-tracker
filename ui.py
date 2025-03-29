from PySide2 import QtWidgets, QtCore, QtGui
import sqlite3
import sys
from datetime import datetime, timedelta
import os
import json


class ActivityMonitorUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Activity Monitor")
        self.setGeometry(100, 100, 1500, 800)

        layout = QtWidgets.QVBoxLayout()

        # Filter Section
        filter_group = QtWidgets.QGroupBox("Filters")
        filter_layout = QtWidgets.QGridLayout()

        self.start_date = QtWidgets.QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QtCore.QDate.currentDate().addDays(-7))  # Default to 7 days ago

        self.end_date = QtWidgets.QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QtCore.QDate.currentDate())  # Default to today

        self.username = QtWidgets.QLineEdit()
        self.software = QtWidgets.QLineEdit()

        # Set up autocompletion for username and software fields
        self.username_completer = QtWidgets.QCompleter()
        self.username.setCompleter(self.username_completer)

        self.software_completer = QtWidgets.QCompleter()
        self.software.setCompleter(self.software_completer)

        self.apply_button = QtWidgets.QPushButton("Apply Filters")
        self.apply_button.clicked.connect(self.apply_filters)

        self.clear_button = QtWidgets.QPushButton("Clear Filters")
        self.clear_button.clicked.connect(self.clear_filters)

        filter_layout.addWidget(QtWidgets.QLabel("Start Date:"), 0, 0)
        filter_layout.addWidget(self.start_date, 0, 1, 1, 2)
        filter_layout.addWidget(QtWidgets.QLabel("End Date:"), 0, 3)
        filter_layout.addWidget(self.end_date, 0, 4, 1, 2)

        filter_layout.addWidget(QtWidgets.QLabel("Username:"), 1, 0)
        filter_layout.addWidget(self.username, 1, 1, 1, 2)
        filter_layout.addWidget(QtWidgets.QLabel("Software:"), 1, 3)
        filter_layout.addWidget(self.software, 1, 4, 1, 2)

        filter_layout.addWidget(self.apply_button, 2, 0, 1, 3)  # Span across multiple columns
        filter_layout.addWidget(self.clear_button, 2, 3, 1, 3)  # Span across multiple columns

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Table Section
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(9)  # Updated to match database columns
        self.table.setHorizontalHeaderLabels(
            ["User", "Date", "Software", "File", "Start-time", "Active Time", "Idle Time", "Total Time", "End-Time"])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.export_button = QtWidgets.QPushButton("Export to Excel")
        self.export_button.clicked.connect(self.export_to_excel)

        self.refresh_button = QtWidgets.QPushButton("Refresh Data")
        self.refresh_button.clicked.connect(self.load_data)

        self.view_json_button = QtWidgets.QPushButton("View User JSON")
        self.view_json_button.clicked.connect(self.view_user_json)

        # Add button to load from JSON
        self.load_json_button = QtWidgets.QPushButton("Load From JSON")
        self.load_json_button.clicked.connect(self.load_from_json)

        button_layout.addWidget(self.export_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.view_json_button)
        button_layout.addWidget(self.load_json_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Load initial data
        self.load_data()

    def connect_to_db(self):
        try:
            conn = sqlite3.connect('activity_monitor.db')
            return conn
        except sqlite3.Error as e:
            QtWidgets.QMessageBox.critical(self, "Database Error", f"Could not connect to database: {str(e)}")
            return None

    def format_time_seconds_to_hms(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    def load_data(self):
        conn = self.connect_to_db()
        if not conn:
            return

        cursor = conn.cursor()

        # Build query based on current filter settings
        query = '''
        SELECT username, log_date, software, start_file, end_file, start_time, 
               active_time, idle_time, total_time, end_time
        FROM activity_logs
        WHERE 1=1
        '''

        params = []

        # Add filter conditions if they are set
        if self.start_date.date() != QtCore.QDate(2000, 1, 1):
            query += " AND log_date >= ?"
            params.append(self.start_date.date().toString("yyyy-MM-dd"))

        if self.end_date.date() != QtCore.QDate(2099, 12, 31):
            query += " AND log_date <= ?"
            params.append(self.end_date.date().toString("yyyy-MM-dd"))

        if self.username.text():
            query += " AND username LIKE ?"
            params.append(f"%{self.username.text()}%")

        if self.software.text():
            query += " AND software LIKE ?"
            params.append(f"%{self.software.text()}%")

        query += " ORDER BY log_date DESC, start_time DESC"

        try:
            cursor.execute(query, params)
            records = cursor.fetchall()

            # Clear existing table data
            self.table.setRowCount(0)

            # Populate table with data
            for row_idx, record in enumerate(records):
                self.table.insertRow(row_idx)

                # Format times to HH:MM:SS format
                active_time_formatted = self.format_time_seconds_to_hms(record[6])
                idle_time_formatted = self.format_time_seconds_to_hms(record[7])
                total_time_formatted = self.format_time_seconds_to_hms(record[8])

                # Format the file display as "start_file ---> end_file"
                file_display = f"{record[3]} ---> {record[4]}"

                # Set data in table cells
                self.table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(record[0]))  # username
                self.table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(record[1]))  # date
                self.table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(record[2]))  # software
                self.table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(file_display))  # formatted file path
                self.table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(record[5]))  # start time
                self.table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(active_time_formatted))  # active time
                self.table.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(idle_time_formatted))  # idle time
                self.table.setItem(row_idx, 7, QtWidgets.QTableWidgetItem(total_time_formatted))  # total time
                self.table.setItem(row_idx, 8, QtWidgets.QTableWidgetItem(record[9]))  # end time

            # Update status message with count of records
            self.setWindowTitle(f"Activity Monitor - {len(records)} records found")

        except sqlite3.Error as e:
            QtWidgets.QMessageBox.critical(self, "Query Error", f"Error loading data: {str(e)}")
        finally:
            conn.close()

        # Update the completers with current data
        self.update_completers()

    def update_completers(self):
        conn = self.connect_to_db()
        if not conn:
            return

        cursor = conn.cursor()

        # Get unique usernames
        cursor.execute("SELECT DISTINCT username FROM activity_logs")
        usernames = [row[0] for row in cursor.fetchall()]
        username_model = QtCore.QStringListModel(usernames)
        self.username_completer.setModel(username_model)

        # Get unique software names
        cursor.execute("SELECT DISTINCT software FROM activity_logs")
        software_names = [row[0] for row in cursor.fetchall()]
        software_model = QtCore.QStringListModel(software_names)
        self.software_completer.setModel(software_model)

        conn.close()

    def load_from_json(self):
        """Load activity data from JSON files instead of database"""
        # Ask user to select a directory where JSON files are stored
        json_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select Directory with JSON Files", "",
            QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
        )

        if not json_dir or not os.path.isdir(json_dir):
            return

        # Look for JSON files in the directory
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        if not json_files:
            QtWidgets.QMessageBox.warning(self, "No JSON Files", f"No JSON files found in {json_dir}")
            return

        # Clear existing table data
        self.table.setRowCount(0)

        # Load data from each JSON file
        row_idx = 0
        for json_file in json_files:
            try:
                with open(os.path.join(json_dir, json_file), 'r') as f:
                    data = json.load(f)

                    # Process each activity record in the JSON file
                    if isinstance(data, dict) and 'activities' in data:
                        activities = data['activities']
                        for activity in activities:
                            # Extract fields that match our table
                            username = data.get('username', 'Unknown')
                            log_date = activity.get('date', 'Unknown')
                            software = activity.get('software', 'Unknown')
                            start_file = activity.get('start_file', '')
                            end_file = activity.get('end_file', '')
                            start_time = activity.get('start_time', '')
                            active_time = activity.get('active_time', 0)  # in seconds
                            idle_time = activity.get('idle_time', 0)  # in seconds
                            total_time = active_time + idle_time  # in seconds
                            end_time = activity.get('end_time', '')

                            # Format times
                            active_time_formatted = self.format_time_seconds_to_hms(active_time)
                            idle_time_formatted = self.format_time_seconds_to_hms(idle_time)
                            total_time_formatted = self.format_time_seconds_to_hms(total_time)

                            # Format file display
                            file_display = f"{start_file} ---> {end_file}"

                            # Add to table
                            self.table.insertRow(row_idx)
                            self.table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(username))
                            self.table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(log_date))
                            self.table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(software))
                            self.table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(file_display))
                            self.table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(start_time))
                            self.table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(active_time_formatted))
                            self.table.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(idle_time_formatted))
                            self.table.setItem(row_idx, 7, QtWidgets.QTableWidgetItem(total_time_formatted))
                            self.table.setItem(row_idx, 8, QtWidgets.QTableWidgetItem(end_time))

                            row_idx += 1
            except Exception as e:
                print(f"Error loading JSON file {json_file}: {str(e)}")

        # Update status message with count of records
        self.setWindowTitle(f"Activity Monitor - {row_idx} records loaded from JSON")

        # We don't update completers here since we're not using the database

        # Inform user
        if row_idx > 0:
            QtWidgets.QMessageBox.information(
                self, "JSON Data Loaded", f"Successfully loaded {row_idx} records from JSON files"
            )
        else:
            QtWidgets.QMessageBox.warning(
                self, "No Data Found", "No valid activity records found in JSON files"
            )

    def apply_filters(self):
        self.load_data()

    def clear_filters(self):
        self.start_date.setDate(QtCore.QDate.currentDate().addDays(-7))
        self.end_date.setDate(QtCore.QDate.currentDate())
        self.username.clear()
        self.software.clear()
        self.load_data()

    def export_to_excel(self):
        try:
            import pandas as pd
            from PySide2.QtWidgets import QFileDialog

            # Get data from the table
            data = []
            for row in range(self.table.rowCount()):
                row_data = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)

            # Create DataFrame
            df = pd.DataFrame(data, columns=[
                "User", "Date", "Software", "File", "Start-time",
                "Active Time", "Idle Time", "Total Time", "End-Time"
            ])

            # Ask user where to save the file
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Excel File", "", "Excel Files (*.xlsx)"
            )

            if file_path:
                if not file_path.endswith('.xlsx'):
                    file_path += '.xlsx'
                df.to_excel(file_path, index=False)
                QtWidgets.QMessageBox.information(
                    self, "Export Successful", f"Data exported to {file_path}"
                )
        except ImportError:
            QtWidgets.QMessageBox.warning(
                self, "Export Failed",
                "Please install pandas to use the Excel export feature:\npip install pandas openpyxl"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Export Error", f"Error exporting data: {str(e)}")

    def view_user_json(self):
        # Get selected row
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            QtWidgets.QMessageBox.information(self, "Selection Required", "Please select a row to view its JSON data")
            return

        # Find the row of the first selected item
        row = selected_rows[0].row()

        # Get username and date from the selected row
        username = self.table.item(row, 0).text()
        date = self.table.item(row, 1).text()

        # Check if JSON file exists
        json_file_path = f"user_activity_logs/{username}_{date}.json"
        if not os.path.exists(json_file_path):
            QtWidgets.QMessageBox.warning(self, "File Not Found", f"JSON file for {username} on {date} not found.")
            return

        try:
            # Read JSON file
            with open(json_file_path, 'r') as f:
                user_data = json.load(f)

            # Create a simple dialog to display JSON data
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"JSON Data for {username} on {date}")
            dialog.setMinimumSize(800, 600)

            layout = QtWidgets.QVBoxLayout()

            # Create a text area for JSON display
            text_area = QtWidgets.QTextEdit()
            text_area.setReadOnly(True)
            text_area.setFont(QtGui.QFont("Courier New", 10))
            text_area.setText(json.dumps(user_data, indent=4))

            layout.addWidget(text_area)

            # Add close button
            close_button = QtWidgets.QPushButton("Close")
            close_button.clicked.connect(dialog.close)
            layout.addWidget(close_button)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error reading JSON file: {str(e)}")


if __name__ == "__main__":
    # Create the database with dummy data if it doesn't exist
    try:
        import os

        if not os.path.exists('activity_monitor.db'):
            print("Database not found. Creating sample database...")
            from activity_monitor_database import create_activity_database

            create_activity_database()
    except ImportError:
        print("Could not import database creation module.")
    except Exception as e:
        print(f"Error setting up database: {str(e)}")

    # Start the application
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # Set application style to Fusion
    window = ActivityMonitorUI()
    window.show()
    sys.exit(app.exec_())