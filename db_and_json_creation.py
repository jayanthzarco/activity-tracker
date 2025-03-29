import sqlite3
import random
from datetime import datetime, timedelta
import os
import json


def create_activity_database():
    # Remove existing database if it exists
    if os.path.exists('activity_monitor.db'):
        os.remove('activity_monitor.db')

    # Create directory for JSON files if it doesn't exist
    json_dir = 'user_activity_logs'
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    else:
        # Clean up existing JSON files
        for file in os.listdir(json_dir):
            os.remove(os.path.join(json_dir, file))

    # Connect to database
    conn = sqlite3.connect('activity_monitor.db')
    cursor = conn.cursor()

    # Create table
    cursor.execute('''
    CREATE TABLE activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        log_date DATE NOT NULL,
        software TEXT NOT NULL,
        start_file TEXT,
        end_file TEXT,
        start_time DATETIME NOT NULL,
        active_time INTEGER NOT NULL,  -- in seconds
        idle_time INTEGER NOT NULL,    -- in seconds
        total_time INTEGER NOT NULL,   -- in seconds
        end_time DATETIME NOT NULL
    )
    ''')

    # Generate sample data
    usernames = ['john.doe', 'jane.smith', 'robert.johnson', 'lisa.wang', 'mike.davis']
    software_list = ['Photoshop', 'Visual Studio Code', 'Microsoft Word', 'Google Chrome', 'AutoCAD', 'Excel',
                     'PowerPoint']

    # File name patterns for each software
    file_patterns = {
        'Photoshop': {
            'start': ['raw_image_{}.psd', 'photo_{}_draft.psd', 'project_{}_initial.psd'],
            'end': ['final_image_{}.psd', 'photo_{}_final.psd', 'project_{}_complete.psd']
        },
        'Visual Studio Code': {
            'start': ['module_{}.py', 'component_{}.js', 'feature_{}_draft.cpp'],
            'end': ['module_{}_final.py', 'component_{}_complete.js', 'feature_{}_tested.cpp']
        },
        'Microsoft Word': {
            'start': ['document_{}_draft.docx', 'report_{}_v1.docx', 'notes_{}.docx'],
            'end': ['document_{}_final.docx', 'report_{}_final.docx', 'notes_{}_complete.docx']
        },
        'Google Chrome': {
            'start': ['https://docs.google.com/document/d/{}', 'https://mail.google.com/mail/{}',
                      'https://github.com/repo/{}'],
            'end': ['https://docs.google.com/document/d/{}/edit', 'https://mail.google.com/mail/{}/sent',
                    'https://github.com/repo/{}/pull/42']
        },
        'AutoCAD': {
            'start': ['blueprint_{}_initial.dwg', 'design_{}_draft.dwg', 'layout_{}.dwg'],
            'end': ['blueprint_{}_final.dwg', 'design_{}_approved.dwg', 'layout_{}_complete.dwg']
        },
        'Excel': {
            'start': ['data_{}_raw.xlsx', 'spreadsheet_{}.xlsx', 'finances_{}_draft.xlsx'],
            'end': ['data_{}_processed.xlsx', 'spreadsheet_{}_final.xlsx', 'finances_{}_approved.xlsx']
        },
        'PowerPoint': {
            'start': ['presentation_{}_outline.pptx', 'slides_{}_draft.pptx', 'deck_{}.pptx'],
            'end': ['presentation_{}_final.pptx', 'slides_{}_complete.pptx', 'deck_{}_presented.pptx']
        }
    }

    # Generate activity data for each user
    all_records = []

    # Generate records for the past 30 days
    today = datetime.now()

    for day_offset in range(30, 0, -1):
        current_date = today - timedelta(days=day_offset)
        date_str = current_date.strftime('%Y-%m-%d')

        # Each user has 3-7 activity records per day
        for username in usernames:
            num_activities = random.randint(3, 7)
            user_daily_records = []

            for _ in range(num_activities):
                # Select random software
                software = random.choice(software_list)

                # Generate random file identifiers
                file_id = random.randint(1000, 9999)

                # Get start and end file names
                start_pattern = random.choice(file_patterns[software]['start'])
                end_pattern = random.choice(file_patterns[software]['end'])

                start_file = start_pattern.format(file_id)
                end_file = end_pattern.format(file_id)

                # Generate random start time for the day
                hour = random.randint(8, 17)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)

                start_time = datetime.strptime(f"{date_str} {hour}:{minute}:{second}", "%Y-%m-%d %H:%M:%S")

                # Generate random active and idle times
                active_time = random.randint(300, 7200)  # 5 minutes to 2 hours
                idle_time = random.randint(0, 900)  # 0 to 15 minutes
                total_time = active_time + idle_time

                # Calculate end time
                end_time = start_time + timedelta(seconds=total_time)

                # Create record
                record = {
                    'username': username,
                    'log_date': date_str,
                    'software': software,
                    'start_file': start_file,
                    'end_file': end_file,
                    'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'active_time': active_time,
                    'idle_time': idle_time,
                    'total_time': total_time,
                    'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S')
                }

                user_daily_records.append(record)
                all_records.append(record)

                # Insert record into database
                cursor.execute('''
                INSERT INTO activity_logs 
                (username, log_date, software, start_file, end_file, start_time, active_time, idle_time, total_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    username,
                    date_str,
                    software,
                    start_file,
                    end_file,
                    start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    active_time,
                    idle_time,
                    total_time,
                    end_time.strftime('%Y-%m-%d %H:%M:%S')
                ))

            # Create JSON file for this user's daily activity
            if user_daily_records:
                json_filename = f"{json_dir}/{username}_{date_str}.json"
                with open(json_filename, 'w') as json_file:
                    json.dump(user_daily_records, json_file, indent=4)

    # Create a JSON file with all activities
    with open(f"{json_dir}/all_activities.json", 'w') as json_file:
        json.dump(all_records, json_file, indent=4)

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print(f"Database created successfully with {len(all_records)} sample records.")
    print(f"JSON files created in the '{json_dir}' directory.")


def load_data_from_db():
    """Function to demonstrate how to load data from the database for the UI"""
    conn = sqlite3.connect('activity_monitor.db')
    cursor = conn.cursor()

    # Example query that could be used with the UI filters
    cursor.execute('''
    SELECT username, log_date, software, start_file, end_file, start_time, 
           active_time, idle_time, total_time, end_time
    FROM activity_logs
    ORDER BY log_date DESC, start_time DESC
    LIMIT 20
    ''')

    records = cursor.fetchall()

    # Print some sample records
    print("Sample records:")
    for record in records[:5]:
        # Format times to be more readable
        active_time_min = record[6] // 60
        idle_time_min = record[7] // 60
        total_time_min = record[8] // 60

        print(f"User: {record[0]}, Date: {record[1]}, Software: {record[2]}")
        print(f"Files: {record[3]} ---> {record[4]}")
        print(f"Time: {record[5]} to {record[9]}")
        print(f"Activity: {active_time_min} min active, {idle_time_min} min idle, {total_time_min} min total")
        print("-" * 50)

    conn.close()


if __name__ == "__main__":
    create_activity_database()
    load_data_from_db()