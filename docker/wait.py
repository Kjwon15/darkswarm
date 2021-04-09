import json
import os

from os import path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

FNAME_CMD = '/tmp/cmd.json'
FNAME_FLAG = '/tmp/cmd.flag'


class CreateEventHandler(FileSystemEventHandler):

    def __init__(self, observer: Observer, p: str):
        self.observer = observer
        self.p = p

    def on_created(self, event):
        if event.src_path == self.p:
            self.observer.stop()


if not path.exists(FNAME_FLAG):
    observer = Observer()
    event_handler = CreateEventHandler(observer, FNAME_FLAG)
    observer.schedule(
        event_handler,
        path=path.dirname(FNAME_FLAG), recursive=False)
    observer.start()
    observer.join()

print('Got cmd')

with open(FNAME_CMD) as f:
    cmd = json.load(f)
    print(cmd)
    os.execvp(cmd[0], cmd)
