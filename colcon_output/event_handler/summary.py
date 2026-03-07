# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import time

import colorama

from colcon_core.event.job import JobEnded
from colcon_core.event.job import JobQueued
from colcon_core.event.output import StderrLine
from colcon_core.event.test import TestFailure
from colcon_core.event_handler import EventHandlerExtensionPoint
from colcon_core.event_handler import format_duration
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
        colorama.init()
        satisfies_version(
            EventHandlerExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')
        self._queued = set()
        self._with_stderr = set()
        self._with_test_failures = set()
        self._ended = set()
        self._failed = set()
        self._interrupted = set()
        self._start_time = time.monotonic()

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

        duration = time.monotonic() - self._start_time
        duration_string = format_duration(duration)

        count, job_type, _ = _msg_arguments(
            self._ended - self._interrupted - self._failed)
        print(colorama.Fore.YELLOW + colorama.Style.BRIGHT + 'Summary: ' +
              colorama.Fore.RESET + str(count) + colorama.Style.NORMAL + ' ' +
              job_type + ' finished [' + colorama.Fore.YELLOW +
              duration_string + colorama.Fore.RESET + ']')

        if self._failed:
            count, job_type, names = _msg_arguments(self._failed)
            print(colorama.Fore.RED +
                  '  {count} {job_type} failed: '.format_map(locals()) +
                  colorama.Style.RESET_ALL + names)

        if self._interrupted:
            count, job_type, names = _msg_arguments(self._interrupted)
            print(colorama.Fore.RED +
                  '  {count} {job_type} aborted: '.format_map(locals()) +
                  colorama.Style.RESET_ALL + names)

        if self._with_stderr:
            count, job_type, names = _msg_arguments(self._with_stderr)
            print(colorama.Fore.YELLOW +
                  '  {count} {job_type} had stderr output: '
                  .format_map(locals()) +
                  colorama.Style.RESET_ALL + names)

        if self._with_test_failures:
            count, job_type, names = _msg_arguments(
                self._with_test_failures)
            print(colorama.Fore.RED +
                  '  {count} {job_type} had test failures: '
                  .format_map(locals()) +
                  colorama.Style.RESET_ALL + names)

        if len(self._queued) > len(self._ended):
            count = len(self._queued - self._ended)
            job_type = get_job_type_word_form(count)
            print(colorama.Fore.BLACK + '  {count} {job_type} not processed'
                  .format_map(locals()) + colorama.Style.RESET_ALL)


def _msg_arguments(jobs):
    return (
        len(jobs),
        get_job_type_word_form(len(jobs)),
        ' '.join(sorted(j.task.context.pkg.name for j in jobs)),
    )


def get_job_type_word_form(job_count):
    """
    Get the singular / plural word form of a job type.

    While this function only returns "package" or "packages" it allows external
    code to replace the function with custom logic.

    :param job_count: The number of jobs
    :rtype: str
    """
    return 'package' if job_count == 1 else 'packages'
