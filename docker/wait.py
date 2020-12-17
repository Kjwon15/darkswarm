import json
import os
import time

from os import path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

FNAME = '/tmp/cmd.json'


class CreateEventHandler(FileSystemEventHandler):

    def __init__(self, observer: Observer, p: str):
        self.observer = observer
        self.p = p

    def on_created(self, event):
        if event.src_path == self.p:
            self.observer.stop()


if not path.exists(FNAME):
    observer = Observer()
    event_handler = CreateEventHandler(observer, FNAME)
    observer.schedule(event_handler, path=path.dirname(FNAME), recursive=False)
    observer.start()
    observer.join()

print('Got cmd')

# Sleep 1s to reduce race condition
time.sleep(1)

with open(FNAME) as f:
    cmd = json.load(f)
    print(cmd)
    os.execvp(cmd[0], cmd)
