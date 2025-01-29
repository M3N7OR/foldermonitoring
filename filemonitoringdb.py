import sys
import time
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

# Function to insert log into MySQL
def log_to_mysql(event_type, src_path, event_description):
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Insert event log into the database
        cursor.execute("""
            INSERT INTO logs (timestamp, event_type, src_path, event_description)
            VALUES (NOW(), %s, %s, %s)
        """, (event_type, src_path, event_description))

        # Commit the transaction
        connection.commit()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        if connection.is_connected():
            connection.close()

# Custom event handler to log events to MySQL
class MyLoggingEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        log_to_mysql("modified", event.src_path, f"Modified: {event.src_path}")
    
    def on_created(self, event):
        log_to_mysql("created", event.src_path, f"Created: {event.src_path}")
    
    def on_deleted(self, event):
        log_to_mysql("deleted", event.src_path, f"Deleted: {event.src_path}")
    
    def on_moved(self, event):
        log_to_mysql("moved", event.src_path, f"Moved from {event.src_path} to {event.dest_path}")

if __name__ == "__main__":
    path = "C:/Users/M3N7OR/Desktop/Folder-monitoring"

    event_handler = MyLoggingEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        print("Monitoring")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("Done")
    finally:
        print("All Done")
    observer.join()
