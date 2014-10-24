#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import re
import sys
import subprocess
try:
    import Queue
except:
    # py3k
    import queue as Queue

import logging
import time
import threading
import optparse
from importlib import import_module

logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.INFO)

from subprocess import PIPE
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

TEST = False

SENTINEL = object()

IGNORE_EXTENSIONS = ('pyc', 'pyo', 'tmp')
IGNORE_DIRS = ('.bzr', '.git', '.hg', '.darcs', '.svn', '.tox', 'docs')
IGNORE_PATTERN = ('.*\\.coverage\\.',)


def log_t(line, *args):
    if args:
        line += ' '.join([str(arg) for arg in args])
    if not TEST:
        logging.warning(line)


def log_args_t(args):
    log_t(' '.join(args))


def run_for_all_apps(path):
    os.chdir(path)

    log_args_t(["./manage.py", "test"])
    if TEST:
        output = subprocess.Popen(["./manage.py", "test"], stdout=PIPE,
                                  stderr=PIPE)
    else:
        output = subprocess.Popen(["./manage.py", "test"])
    return output.communicate()[1]


def run_for_apps(path, apps):
    os.chdir(path)
    log_args_t(["./manage.py", "test"] + apps)
    if TEST:
        output = subprocess.Popen(["./manage.py", "test"] + apps, stdout=PIPE,
                                  stderr=PIPE)
    else:
        output = subprocess.Popen(["./manage.py", "test"] + apps)
    return output.communicate()[1]


class Consumer(threading.Thread):

    def __init__(self, apps, path, queue, lock, *args, **kwargs):
        super(Consumer, self).__init__(*args, **kwargs)
        self.queue = queue
        self.lock = lock
        self.known = {}
        self.path = path
        for app in apps:
            self.known[app] = os.path.join(path, app)

    def test(self, targets):
        log_t("changes in ", targets)
        targets_set = set()
        for target in targets:
            for app in self.known:
                if target.startswith(self.known[app]):
                    targets_set.add(app)
                    break
            else:
                targets_set.add('_all_')
                break
        if '_all_' in targets_set:
            run_for_all_apps(self.path)
        else:
            run_for_apps(self.path, list(targets_set))

    def halt(self):
        self.done = True

    # Path manipulation
    def include(self, path):
        """Returns `True` if the file is not ignored"""
        for extension in IGNORE_EXTENSIONS:
            if path.endswith(extension):
                return False
        parts = path.split(os.path.sep)
        for part in parts:
            if part in IGNORE_DIRS:
                return False
        for pattern in IGNORE_PATTERN:
            if re.match(pattern, path):
                return False
        return True

    def filter_targets(self, targets):
        cleaned = []
        for target in targets:
            if self.include(target):
                cleaned.append(target)
            else:
                self.queue.task_done()
        return cleaned

    def run(self):
        log_t("Waiting for changes...")
        self.done = False
        while not self.done:
            self.lock.acquire()
            if not self.queue.empty():
                targets = []
                while not self.queue.empty() and not self.done:
                    target = self.queue.get()
                    if target is not SENTINEL:

                        targets.append(target)
                    else:
                        self.queue.task_done()
                        self.done = True
                targets = self.filter_targets(targets)
                if targets:
                    self.test(targets)
                    log_t("Waiting for changes...")
                    for _ in targets:
                        self.queue.task_done()
            self.lock.release()
            if not self.done:
                time.sleep(1)


class EventHandler(FileSystemEventHandler):

    def __init__(self, consumer, queue, *args, **kwargs):
        self.consumer = consumer
        self.queue = queue
        return super(EventHandler, self).__init__(*args, **kwargs)

    def on_any_event(self, event):
        if not event.is_directory:
            self.queue.put(event.src_path)
            if hasattr(event, 'dest_path'):
                self.queue.put(event.dest_path)


class Watcher(object):

    def __init__(self, path, settings):
        self.path = path
        self.lock = threading.Lock()
        settings = settings
        self.apps = settings.INSTALLED_APPS

    def start(self):
        self.paused = False
        self.observer = Observer()
        self.queue = Queue.Queue()
        self.consumer = Consumer(self.apps, self.path, self.queue, self.lock)
        self.consumer.start()
        event_handler = EventHandler(self.consumer, self.queue)
        self.observer.schedule(event_handler, self.path, recursive=True)
        self.observer.start()

    def pause(self):
        self.paused = not self.paused
        if self.paused:
            self.lock.acquire()
        else:
            self.lock.release()

    def stop(self):
        self.observer.stop()
        self.observer.join()
        self.queue.put(SENTINEL)
        self.queue.join()


def parse_args():
    parser = optparse.OptionParser()
    parser.usage = """Usage: %[prog] [options] [<path>]"""

    parser.add_option("-s", "--settings", dest='settings',
                      help="Django settings module ie: proj_name.settings. "
                      "The default will try to guess from the path passed or "
                      u"by using the currrent directory.")
    opt, args = parser.parse_args(sys.argv)

    path = args[1] if len(args) > 1 else os.getcwdu()

    if opt.settings:
        settings_module = opt.settings

    else:
        settings_module = os.path.basename(os.getcwdu()) + '.settings'

    settings = import_module(settings_module)

    return (path, settings)


def watch():

    path, settings = parse_args()
    log_t("Using settings: %s" % settings)
    watcher = Watcher(path, settings)
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.consumer.halt()
        sys.exit(0)
