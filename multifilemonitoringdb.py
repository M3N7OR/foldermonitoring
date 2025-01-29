import sys
import time
import os
import logging
import mysql.connector
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# MySQL connection details
DB_CONFIG = {
    'user': 'root',
    'host': 'localhost',
    'database': 'file_monitoring',
}

# Function to insert log into MySQL for specific path-based table
def log_to_mysql(event_type, src_path, event_description, path_name):
    try:
        # Use the path name to dynamically generate the table name
        table_name = f"{path_name}_logs"
        shortened_path = os.path.basename(src_path)
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Create table dynamically if it doesn't exist already
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                timestamp TIMESTAMP,
                event_type VARCHAR(50),
                src_path TEXT,
                event_description TEXT
            )
        """)

        # Insert event log into the specific path-based table
        cursor.execute(f"""
            INSERT INTO {table_name} (event_type, src_path, event_description)
            VALUES (%s, %s, %s)
        """, (event_type, shortened_path, event_description))

        # Commit the transaction
        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if connection.is_connected():
            connection.close()

# Custom event handler to log events to MySQL for specific paths
class MyLoggingEventHandler(FileSystemEventHandler):
    def __init__(self, path_name):
        self.path_name = path_name
    
    def on_modified(self, event):
        log_to_mysql("modified", event.src_path, f"Modified: {event.src_path}", self.path_name)
    
    def on_created(self, event):
        log_to_mysql("created", event.src_path, f"Created: {event.src_path}", self.path_name)
    
    def on_deleted(self, event):
        log_to_mysql("deleted", event.src_path, f"Deleted: {event.src_path}", self.path_name)
    
    def on_moved(self, event):
        log_to_mysql("moved", event.src_path, f"Moved from {event.src_path} to {event.dest_path}", self.path_name)

if __name__ == "__main__":
    paths = [
        "C:/Users/M3N7OR/Documents", 
        "C:/Users/M3N7OR/Downloads",
    ]

    # Set up observers for each directory
    observers = []
    for path in paths:
        event_handler = MyLoggingEventHandler(path.split("/")[-1].split("\\")[-1])  # Use the last part of the path as table name suffix
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        observers.append(observer)
    
    try:
        print("Monitoring multiple paths...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop all observers gracefully
        for observer in observers:
            observer.stop()
        print("Done")
    for observer in observers:
        observer.join()
