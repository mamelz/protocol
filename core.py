"""Module for the main class 'Protocol'."""
from __future__ import annotations

from typing import Sequence

from .schedule import Schedule


class Protocol:

    def __init__(self, schedules: Sequence[Schedule]):
        self._schedules = tuple(schedules)
        labels = set()
        for sch in self._schedules:
            if sch.label in labels:
                raise ValueError(f"Duplicate schedule label {sch.label}")
            labels |= sch.label

        self.results = {}

    @property
    def _map(self):
        labels = (sch.label for sch in self._schedules)
        return dict(zip(labels, self._schedules))

    def add_schedule(self, schedule: Schedule):
        """Add a schedule.

        Args:
            schedule (Schedule): The schedule to add.

        Raises:
            ValueError: Raised, if the label of the schedule already exists.
        """
        if schedule.label in self._map:
            raise ValueError(f"Schedule label {schedule.label} already"
                             " exists.")
        self._schedules += (schedule,)

    def duplicate_schedule(self, source_label: str, target_label: str):
        """Add copy of an already schedule.

        Args:
            source_label (str): Label of the schedule to copy.
            target_label (str): Label of the newly created schedule.
        """
        self.add_schedule(Schedule(self._map[source_label]._configuration,
                                   target_label))

    def perform(self, schedule_label=None):

        if schedule_label is not None:
            sch = self._map[schedule_label]
            sch.perform()
            self.results[schedule_label] = sch.results
        else:
            for sch in self._schedules:
                sch.perform()
                self.results[sch.label] = sch.results

    def setup(self, schedule_label=None, start_time=None):
        """Set up schedules for execution.

        If label is given, sets up the specified schedule. Otherwise, sets up
        all schedules.
        Args:
            schedule_label (str, optional): Label of a schedule.
                Defaults to None.
            start_time (float, optional): A start time overriding the schedule
                configuration. Defaults to None.
        """
        if schedule_label is not None:
            self._map[schedule_label].setup(start_time)
        else:
            for sch in self._schedules:
                sch.setup(start_time)
