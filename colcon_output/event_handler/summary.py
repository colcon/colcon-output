# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import time

from colcon_core.event.job import JobEnded
from colcon_core.event.job import JobQueued
from colcon_core.event.output import StderrLine
from colcon_core.event.test import TestFailure
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.event_reactor import EventReactorShutdown
from colcon_core.plugin_system import satisfies_version
from colcon_core.subprocess import SIGINT_RESULT


class SummaryHandler(EventHandlerExtensionPoint):
    """
    Output summary of all tasks.

    The extension handles events of the following types:
    - :py:class:`colcon_core.event.output.StderrLine`
    - :py:class:`colcon_core.event.job.JobEnded`
    - :py:class:`colcon_core.event.job.JobQueued`
    - :py:class:`colcon_core.event.test.TestFailure`
    - :py:class:`colcon_core.event_reactor.EventReactorShutdown`
    """

    # the priority should be lower than other extensions
    # in order to not output the summary before they are finished
    PRIORITY = 50

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self._queued = set()
        self._with_stderr = set()
        self._with_test_failures = set()
        self._ended = set()
        self._failed = set()
        self._interrupted = set()
        self._start_time = time.time()

    def __call__(self, event):  # noqa: D102
        data = event[0]

        if isinstance(data, JobQueued):
            job = event[1]
            self._queued.add(job)
        elif isinstance(data, StderrLine):
            job = event[1]
            self._with_stderr.add(job)
        elif isinstance(data, TestFailure):
            job = event[1]
            self._with_test_failures.add(job)
        elif isinstance(data, JobEnded):
            job = event[1]
            self._ended.add(job)
            if data.rc == SIGINT_RESULT:
                self._interrupted.add(job)
            elif data.rc:
                self._failed.add(job)
        elif isinstance(data, EventReactorShutdown):
            self._print_summary()

    def _print_summary(self):
        # separate the summary from the previous output
        print()

        duration = time.time() - self._start_time

        count, plural_suffix, _ = _msg_arguments(
            self._ended - self._interrupted - self._failed)
        print('Summary: {count} package{plural_suffix} finished '
              '[{duration:.2f}s]'.format_map(locals()))

        if self._failed:
            count, plural_suffix, names = _msg_arguments(self._failed)
            print('  {count} package{plural_suffix} failed: {names}'
                  .format_map(locals()))

        if self._interrupted:
            count, plural_suffix, names = _msg_arguments(self._interrupted)
            print('  {count} package{plural_suffix} aborted: {names}'
                  .format_map(locals()))

        if self._with_stderr:
            count, plural_suffix, names = _msg_arguments(self._with_stderr)
            print(
                '  {count} package{plural_suffix} had stderr output: {names}'
                .format_map(locals()))

        if self._with_test_failures:
            count, plural_suffix, names = _msg_arguments(
                self._with_test_failures)
            print(
                '  {count} package{plural_suffix} had test failures: {names}'
                .format_map(locals()))

        if len(self._queued) > len(self._ended):
            count = len(self._queued - self._ended)
            plural_suffix = 's' if count != 1 else ''
            print(
                '  {count} package{plural_suffix} not processed'
                .format_map(locals()))


def _msg_arguments(jobs):
    return (
        len(jobs),
        's' if len(jobs) != 1 else '',
        ' '.join(sorted(j.task.context.pkg.name for j in jobs)),
    )
