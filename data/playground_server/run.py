"""
run.py

This script is responsible for starting the Flask application with hot-reloading enabled.
It uses the `watchdog` package to monitor changes in the filesystem.

The script runs the application by executing the `app.py` file. If any changes are detected
in the current directory or its subdirectories, it automatically restarts the Flask server.

Usage:
    python run.py
"""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from subprocess import Popen
import time


class MyHandler(FileSystemEventHandler):
    def __init__(self):
        print("starting")
        self.serving = Popen(['python', 'app.py'])

    def on_modified(self, event):
        print(f'Event type: {event.event_type}  path : {event.src_path}')
        self.restart_server()

    def on_created(self, event):
        print(f'Event type: {event.event_type}  path : {event.src_path}')
        self.restart_server()

    def on_deleted(self, event):
        print(f'Event type: {event.event_type}  path : {event.src_path}')
        self.restart_server()

    def restart_server(self):
        if self.serving:
            self.serving.kill()
            self.serving = Popen(['python', 'app.py'])


event_handler = MyHandler()
observer = Observer()
observer.schedule(event_handler, recursive=True, path="./")
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
