from flask import Flask, render_template, send_file, request
import mysql.connector
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import csv
from io import StringIO, BytesIO
import logging
import threading
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# MySQL connection details
DB_CONFIG = {
    'user': 'root',
    'host': 'localhost',
    'database': 'file_monitoring',
}

# Initialize Flask app
app = Flask(__name__)

# Function to insert log into MySQL for specific path-based table
def log_to_mysql(event_type, src_path, event_description, path_name):
    try:
        table_name = f"{path_name}_logs"
        shortened_path = os.path.basename(src_path)
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type VARCHAR(50),
                src_path TEXT,
                event_description TEXT
            )
        """)

        cursor.execute(f"""
            INSERT INTO {table_name} (event_type, src_path, event_description)
            VALUES (%s, %s, %s)
        """, (event_type, shortened_path, event_description))

        connection.commit()
        cursor.close()
        connection.close()
        logging.info(f"Logged event to {table_name}: {event_type} - {src_path}")
    except mysql.connector.Error as err:
        logging.error(f"Error inserting into {table_name}: {err}")
        if 'connection' in locals() and connection.is_connected():
            connection.close()

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

def start_file_monitoring():
    paths = [
        "C:/Users/M3N7OR/Documents", 
        "C:/Users/M3N7OR/Downloads",
    ]

    observers = []
    for path in paths:
        path_name = path.split("/")[-1].split("\\")[-1]
        event_handler = MyLoggingEventHandler(path_name)
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()
        observers.append(observer)
        logging.info(f"Started monitoring: {path}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for observer in observers:
            observer.stop()
        logging.info("Stopped monitoring.")
    for observer in observers:
        observer.join()

def fetch_logs(table_name, date_filter=None, event_type_filter=None, start_date=None, end_date=None, sort_by='timestamp DESC'):
    logs = []
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)
        query = f"SELECT * FROM {table_name}"
        conditions = []
        if date_filter:
            conditions.append(f"DATE(timestamp) = '{date_filter}'")
        if event_type_filter:
            conditions.append(f"event_type = '{event_type_filter}'")
        if start_date and end_date:
            conditions.append(f"DATE(timestamp) BETWEEN '{start_date}' AND '{end_date}'")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += f" ORDER BY {sort_by}"  # Default sorting is by timestamp DESC
        cursor.execute(query)
        logs = cursor.fetchall()
        cursor.close()
        connection.close()
    except mysql.connector.Error as err:
        logging.error(f"Error fetching logs from {table_name}: {err}")
    return logs

@app.route('/')
def index():
    # Default to "Documents" logs
    path_name = request.args.get('path_name', 'Documents')
    date_filter = request.args.get('date_filter')
    event_type_filter = request.args.get('event_type_filter')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    sort_by = request.args.get('sort_by', 'timestamp DESC')
    
    table_name = f"{path_name}_logs"
    logs = fetch_logs(table_name, date_filter, event_type_filter, start_date, end_date, sort_by)
    return render_template('index.html', logs=logs, path_name=path_name, date_filter=date_filter, event_type_filter=event_type_filter, start_date=start_date, end_date=end_date)

@app.route('/export/csv/<path_name>')
def export_logs_csv(path_name):
    # Get filters from query parameters
    date_filter = request.args.get('date_filter')
    event_type_filter = request.args.get('event_type_filter')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    table_name = f"{path_name}_logs"
    logs = fetch_logs(table_name, date_filter, event_type_filter, start_date, end_date)

    text_stream = StringIO()
    writer = csv.writer(text_stream)
    writer.writerow(['Timestamp', 'Event Type', 'Source Path', 'Event Description'])

    for log in logs:
        timestamp_str = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if log.get('timestamp') else ''
        writer.writerow([timestamp_str, log.get('event_type', ''), log.get('src_path', ''), log.get('event_description', '')])

    byte_stream = BytesIO(text_stream.getvalue().encode('utf-8'))
    byte_stream.seek(0)

    return send_file(
        byte_stream,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{path_name}_logs.csv'
    )

@app.route('/export/pdf/<path_name>')
def export_logs_pdf(path_name):
    # Get filters from query parameters
    date_filter = request.args.get('date_filter')
    event_type_filter = request.args.get('event_type_filter')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    table_name = f"{path_name}_logs"
    logs = fetch_logs(table_name, date_filter, event_type_filter, start_date, end_date)

    pdf_stream = BytesIO()
    pdf = canvas.Canvas(pdf_stream, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 50, f"Log Report for {path_name}")

    y_position = height - 80
    pdf.setFont("Helvetica", 10)

    pdf.drawString(50, y_position, "Timestamp")
    pdf.drawString(200, y_position, "Event Type")
    pdf.drawString(350, y_position, "Source Path")
    pdf.drawString(500, y_position, "Description")

    y_position -= 20

    for log in logs:
        timestamp_str = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if log.get('timestamp') else ''
        event_type = log.get('event_type', '')
        src_path = log.get('src_path', '')
        event_description = log.get('event_description', '')

        pdf.drawString(50, y_position, timestamp_str)
        pdf.drawString(200, y_position, event_type)
        pdf.drawString(350, y_position, src_path[:20])
        pdf.drawString(500, y_position, event_description[:20])

        y_position -= 20
        if y_position < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y_position = height - 50

    pdf.save()
    pdf_stream.seek(0)

    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{path_name}_logs.pdf'
    )

def run_file_monitoring():
    logging.info("Starting file monitoring...")
    start_file_monitoring()

if __name__ == "__main__":
    monitoring_thread = threading.Thread(target=run_file_monitoring)
    monitoring_thread.daemon = True
    monitoring_thread.start()
    app.run(debug=True)