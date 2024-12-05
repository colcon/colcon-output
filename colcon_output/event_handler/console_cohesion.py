# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import sys
from collections import defaultdict

from colcon_core.event.job import JobEnded
from colcon_core.event.output import StderrLine
from colcon_core.event.output import StdoutLine
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.plugin_system import satisfies_version
from colcon_core.subprocess import SIGINT_RESULT


class ConsoleCohesionEventHandler(EventHandlerExtensionPoint):
    """
    Pass task output at once to stdout.

    The extension (indirectly) handles events of the following types:
    - :py:class:`colcon_core.event.command.Command`
    - :py:class:`colcon_core.event.output.StdoutLine`
    - :py:class:`colcon_core.event.output.StderrLine`
    """

    # this handler is disabled by default
    # in favor of he `console_direct` or `console_log` handler
    # but other handlers might choose to change that presetting
    ENABLED_BY_DEFAULT = False

    # the priority should be higher than the `console_stderr` handler
    # in order for the `stderr` output to appear below the combined output
    PRIORITY = 130

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self.enabled = ConsoleCohesionEventHandler.ENABLED_BY_DEFAULT
        self._lines = defaultdict(list)
        self.encoding = self.get_encoding()

    def get_encoding(self):
        if sys.platform == 'win32':
            from ctypes import windll
            return str(windll.kernel32.GetConsoleOutputCP())
        return 'utf-8'

    def __call__(self, event):  # noqa: D102
        data = event[0]

        if isinstance(data, (StdoutLine, StderrLine)):
            job = event[1]
            self._lines[job].append(data.line)

        elif isinstance(data, JobEnded):
            job = event[1]
            if self._lines[job] and data.rc != SIGINT_RESULT:
                msg = '--- output: {data.identifier}\n' \
                    .format_map(locals()) + \
                    b''.join(
                        self._lines[job]).decode(encoding=self.encoding) + \
                    '---'
                print(msg, flush=True)
                del self._lines[job]
