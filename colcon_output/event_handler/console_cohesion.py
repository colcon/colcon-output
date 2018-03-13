# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

from colcon_core.event.job import JobEnded
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.plugin_system import satisfies_version
from colcon_output.event_handler.log import get_log_directory
from colcon_output.event_handler.log import STDOUT_STDERR_LOG_FILENAME


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

    # the priority should be lower than the `log` handler
    # since it reads the log file written by that extension
    # the priority should be higher than the `console_stderr` handler
    # in order for the `stderr` output to appear below the combined output
    PRIORITY = 130

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self.enabled = ConsoleCohesionEventHandler.ENABLED_BY_DEFAULT

    def __call__(self, event):  # noqa: D102
        data = event[0]

        # instead of buffering all output in memory
        # read the combined log file written by the `log` event handler
        if isinstance(data, JobEnded):
            job = event[1]
            base_path = get_log_directory(job)
            if not (base_path / STDOUT_STDERR_LOG_FILENAME).exists():
                return
            with (base_path / STDOUT_STDERR_LOG_FILENAME).open(mode='r') as h:
                content = h.read()
            msg = '--- output: {data.identifier}\n'.format_map(locals()) + \
                content + \
                '---'
            print(msg, flush=True)
