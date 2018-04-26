# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import time

from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.location import create_log_path
from colcon_core.location import get_log_path
from colcon_core.plugin_system import satisfies_version


class EventLogEventHandler(EventHandlerExtensionPoint):
    """
    Log all events to a global log file.

    The log file `events.log` is created in the log directory.
    """

    FILENAME = 'events.log'

    # the priority should be higher than the default priority
    # in order to write the events to the log file first
    PRIORITY = 200

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self._path = None
        self._start_time = None

    def __call__(self, event):  # noqa: D102
        data = event[0]

        self._init_log()

        context = str(event[1]) if event[1] is not None else '-'
        try:
            members = data.__dict__
        except AttributeError:
            members = {s: getattr(data, s) for s in data.__slots__}
        with self._path.open(mode='a') as h:
            h.write(
                '[%f] (%s) %s: %s\n' % (
                    self._get_relative_time(), context,
                    data.__class__.__name__, members))

    def _init_log(self):
        # only create log once
        if self._path is not None:
            return

        create_log_path(self.context.args.verb_name)
        self._path = get_log_path() / EventLogEventHandler.FILENAME
        with self._path.open(mode='w'):
            pass

    def _get_relative_time(self):
        now = time.time()
        if self._start_time is None:
            self._start_time = now
            return 0
        return now - self._start_time
