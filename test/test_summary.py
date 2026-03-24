# Copyright 2026 Open Source Robotics Foundation, Inc.
# Licensed under the Apache License, Version 2.0

from pathlib import Path
from unittest.mock import Mock

from colcon_core.event.job import JobEnded
from colcon_core.event.job import JobQueued
from colcon_core.event.output import StderrLine
from colcon_core.event.test import TestFailure as _TestFailure
from colcon_core.event_reactor import EventReactorShutdown
from colcon_core.executor import Job
from colcon_core.package_descriptor import PackageDescriptor
from colcon_core.subprocess import SIGINT_RESULT
from colcon_core.task import TaskContext
from colcon_output.event_handler.summary import SummaryHandler
import pytest


@pytest.fixture
def summary_handler():
    return SummaryHandler()


def _create_mock_job(name, pkg=None):
    if pkg is None:
        pkg = PackageDescriptor(Path('/path/to/' + name))
        pkg.name = name

    context = TaskContext(pkg=pkg, args=None, dependencies=None)

    task = Mock()
    task.context = context

    job = Job(
        identifier=name, dependencies=set(), task=task,
        task_context=context)
    return job


def test_successful_job(summary_handler, capsys):
    job = _create_mock_job('pkg_a')
    summary_handler((JobQueued(job.task_context.pkg.name), job))
    summary_handler((JobEnded('pkg_a', 0), job))
    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()
    assert '1 package finished' in captured.out


def test_failed_job(summary_handler, capsys):
    job = _create_mock_job('pkg_fail')
    summary_handler((JobQueued(job.task_context.pkg.name), job))
    summary_handler((JobEnded('pkg_fail', 1), job))
    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()
    assert '0 packages finished' in captured.out
    assert '1 package failed: pkg_fail' in captured.out


def test_interrupted_job(summary_handler, capsys):
    job = _create_mock_job('pkg_abort')
    summary_handler((JobQueued(job.task_context.pkg.name), job))
    summary_handler((JobEnded('pkg_abort', SIGINT_RESULT), job))
    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()
    assert '0 packages finished' in captured.out
    assert '1 package aborted: pkg_abort' in captured.out


def test_stderr_job(summary_handler, capsys):
    job = _create_mock_job('pkg_stderr')
    summary_handler((JobQueued(job.task_context.pkg.name), job))
    summary_handler((StderrLine(b'error'), job))
    summary_handler((JobEnded('pkg_stderr', 0), job))
    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()
    assert '1 package finished' in captured.out
    assert '1 package had stderr output: pkg_stderr' in captured.out


def test_test_failure_job(summary_handler, capsys):
    job = _create_mock_job('pkg_test_fail')
    summary_handler((JobQueued(job.task_context.pkg.name), job))
    summary_handler((_TestFailure('pkg_test_fail'), job))
    summary_handler((JobEnded('pkg_test_fail', 0), job))
    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()
    assert '1 package finished' in captured.out
    assert '1 package had test failures: pkg_test_fail' in captured.out


def test_blocked_job(summary_handler, capsys):
    job = _create_mock_job('pkg_blocked')
    summary_handler((JobQueued(job.task_context.pkg.name), job))
    # Never ends
    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()
    assert '0 packages finished' in captured.out
    assert '1 package not processed' in captured.out


def test_multi_job_interrupted(summary_handler, capsys):
    # One job succeeds, one job blocked -> the package is considered aborted
    shared_pkg = PackageDescriptor(Path('/path/to/pkg_multi'))
    shared_pkg.name = 'pkg_multi'
    shared_pkg.type = 'mock'

    job1 = _create_mock_job('pkg_multi', pkg=shared_pkg)
    job2 = _create_mock_job('pkg_multi', pkg=shared_pkg)

    summary_handler((JobQueued(job1.task.context.pkg.name), job1))
    summary_handler((JobQueued(job2.task.context.pkg.name), job2))

    summary_handler((JobEnded('pkg_multi', 0), job1))
    # job2 never ends

    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()

    # "interrupted |= ended & blocked - failed" means it's aborted,
    # not finished, not blocked
    assert '0 packages finished' in captured.out
    assert '1 package aborted: pkg_multi' in captured.out


def test_multi_job_failed_early(summary_handler, capsys):
    shared_pkg = PackageDescriptor(Path('/path/to/pkg_multi_fail_early'))
    shared_pkg.name = 'pkg_multi_fail_early'

    job1 = _create_mock_job('pkg_multi_fail_early', pkg=shared_pkg)
    job2 = _create_mock_job('pkg_multi_fail_early', pkg=shared_pkg)

    summary_handler((JobQueued(job1.task.context.pkg.name), job1))
    summary_handler((JobQueued(job2.task.context.pkg.name), job2))

    summary_handler((JobEnded('pkg_multi_fail_early', 1), job1))
    # job2 never ends

    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()

    assert '0 packages finished' in captured.out
    assert '1 package failed: pkg_multi_fail_early' in captured.out


def test_multi_job_failed_late(summary_handler, capsys):
    shared_pkg = PackageDescriptor(Path('/path/to/pkg_multi_fail_late'))
    shared_pkg.name = 'pkg_multi_fail_late'

    job1 = _create_mock_job('pkg_multi_fail_late', pkg=shared_pkg)
    job2 = _create_mock_job('pkg_multi_fail_late', pkg=shared_pkg)

    summary_handler((JobQueued(job1.task.context.pkg.name), job1))
    summary_handler((JobQueued(job2.task.context.pkg.name), job2))

    summary_handler((JobEnded('pkg_multi_fail_late', 0), job1))
    summary_handler((JobEnded('pkg_multi_fail_late', 1), job2))

    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()

    assert '0 packages finished' in captured.out
    assert '1 package failed: pkg_multi_fail_late' in captured.out


def test_multi_job_stderr(summary_handler, capsys):
    shared_pkg = PackageDescriptor(Path('/path/to/pkg_multi_stderr'))
    shared_pkg.name = 'pkg_multi_stderr'

    job1 = _create_mock_job('pkg_multi_stderr', pkg=shared_pkg)
    job2 = _create_mock_job('pkg_multi_stderr', pkg=shared_pkg)

    summary_handler((JobQueued(job1.task.context.pkg.name), job1))
    summary_handler((JobQueued(job2.task.context.pkg.name), job2))

    summary_handler((StderrLine(b'error'), job1))
    summary_handler((JobEnded('pkg_multi_stderr', 0), job1))
    summary_handler((JobEnded('pkg_multi_stderr', 0), job2))

    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()

    assert '1 package finished' in captured.out
    assert '1 package had stderr output: pkg_multi_stderr' in captured.out


def test_multi_job_test_failure(summary_handler, capsys):
    shared_pkg = PackageDescriptor(Path('/path/to/pkg_multi_test_fail'))
    shared_pkg.name = 'pkg_multi_test_fail'

    job1 = _create_mock_job('pkg_multi_test_fail', pkg=shared_pkg)
    job2 = _create_mock_job('pkg_multi_test_fail', pkg=shared_pkg)

    summary_handler((JobQueued(job1.task.context.pkg.name), job1))
    summary_handler((JobQueued(job2.task.context.pkg.name), job2))

    summary_handler((JobEnded('pkg_multi_test_fail', 0), job1))
    summary_handler((_TestFailure('pkg_multi_test_fail'), job2))
    summary_handler((JobEnded('pkg_multi_test_fail', 0), job2))

    summary_handler((EventReactorShutdown(), None))
    captured = capsys.readouterr()

    assert '1 package finished' in captured.out
    assert '1 package had test failures: pkg_multi_test_fail' in captured.out
