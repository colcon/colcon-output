# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import copy
import os

from colcon_core.event.command import Command
from colcon_core.event.output import StderrLine
from colcon_core.event.output import StdoutLine
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.event_handler.console_direct import ConsoleDirectEventHandler
from colcon_core.location import create_log_path
from colcon_core.location import get_log_path
from colcon_core.plugin_system import satisfies_version

# when this extension is present it disables the direct console output
ConsoleDirectEventHandler.ENABLED_BY_DEFAULT = False

COMMAND_LOG_FILENAME = 'command.log'
STDOUT_LOG_FILENAME = 'stdout.log'
STDERR_LOG_FILENAME = 'stderr.log'
STDOUT_STDERR_LOG_FILENAME = 'stdout_stderr.log'
ALL_STREAMS_LOG_FILENAME = 'streams.log'

all_log_filenames = [
    COMMAND_LOG_FILENAME,
    STDOUT_LOG_FILENAME,
    STDERR_LOG_FILENAME,
    STDOUT_STDERR_LOG_FILENAME,
    ALL_STREAMS_LOG_FILENAME,
]


class LogEventHandler(EventHandlerExtensionPoint):
    """
    Output task specific log files.

    The following log files are created in the log directory of the specific
    task: `command.log`, `stdout.log`, `stderr.log`.
    Additionally the log file `streams.log` is created with the combined
    content.

    The presence of this extension disables the default console output in order
    to keep the amount of output readable.

    The extension handles events of the following types:
    - :py:class:`colcon_core.event.command.Command`
    - :py:class:`colcon_core.event.output.StdoutLine`
    - :py:class:`colcon_core.event.output.StderrLine`
    """

    # the priority should be higher than the default priority
    # in order to write the information to the log files before
    PRIORITY = 150

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self._jobs = set()

    def __call__(self, event):  # noqa: D102
        global all_log_filenames
        data = event[0]

        filenames = copy.copy(all_log_filenames)
        if not isinstance(data, Command):
            filenames.remove(COMMAND_LOG_FILENAME)
        if not isinstance(data, StdoutLine):
            filenames.remove(STDOUT_LOG_FILENAME)
        if not isinstance(data, StderrLine):
            filenames.remove(STDERR_LOG_FILENAME)
        if (
            not isinstance(data, StdoutLine) and
            not isinstance(data, StderrLine)
        ):
            filenames.remove(STDOUT_STDERR_LOG_FILENAME)
        if len(filenames) <= 1:
            # skip if event is neither of the known events
            return

        if isinstance(data, Command):
            line = data.to_string() + '\n'
        else:
            line = data.line

        job = event[1]
        self._init_logs(job)

        mode = 'a'
        if isinstance(line, bytes):
            mode += 'b'

        base_path = get_log_directory(job)
        for filename in filenames:
            with (base_path / filename).open(mode=mode) as h:
                h.write(line)

    def _init_logs(self, job):
        global all_log_filenames
        # skip job agnostic events
        if job is None:
            return
        # only create logs once per task
        if job in self._jobs:
            return
        self._jobs.add(job)

        create_log_path(self.context.args.verb_name)
        base_path = get_log_directory(job)
        os.makedirs(str(base_path), exist_ok=True)
        for filename in all_log_filenames:
            with (base_path / filename).open(mode='w'):
                pass


def get_log_directory(job):
    """
    Get the log directory for a specific job.

    :param job: The job
    :rtype: Path
    """
    return get_log_path() / job.identifier
