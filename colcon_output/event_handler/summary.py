# Copyright 2016-2018 Dirk Thomas
# Licensed under the Apache License, Version 2.0

import time

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

        blocked_jobs = self._queued - self._ended

        # convert jobs to package names
        ended = {j.task_context.pkg for j in self._ended}
        interrupted = {j.task_context.pkg for j in self._interrupted}
        failed = {j.task_context.pkg for j in self._failed}
        with_stderr = {j.task_context.pkg for j in self._with_stderr}
        with_test_failures = {
            j.task_context.pkg for j in self._with_test_failures}
        blocked = {j.task_context.pkg for j in blocked_jobs}

        # packages with successful jobs and blocked jobs are "interrupted"
        interrupted |= ended & blocked - failed

        # truly "blocked" packages have no jobs attempted
        blocked -= ended

        count, job_type, _ = _msg_arguments(ended - interrupted - failed)
        print('Summary: {count} {job_type} finished '
              '[{duration_string}]'.format_map(locals()))

        if failed:
            count, job_type, names = _msg_arguments(failed)
            print('  {count} {job_type} failed: {names}'
                  .format_map(locals()))

        if interrupted:
            count, job_type, names = _msg_arguments(interrupted)
            print('  {count} {job_type} aborted: {names}'
                  .format_map(locals()))

        if with_stderr:
            count, job_type, names = _msg_arguments(with_stderr)
            print(
                '  {count} {job_type} had stderr output: {names}'
                .format_map(locals()))

        if with_test_failures:
            count, job_type, names = _msg_arguments(with_test_failures)
            print(
                '  {count} {job_type} had test failures: {names}'
                .format_map(locals()))

        if blocked:
            count = len(blocked)
            job_type = get_job_type_word_form(count)
            print(
                '  {count} {job_type} not processed'
                .format_map(locals()))


def _msg_arguments(packages):
    return (
        len(packages),
        get_job_type_word_form(len(packages)),
        ' '.join(sorted(p.name for p in packages)),
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
