from __future__ import annotations 

import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence
from math import gcd

TICKS_PER_TIME_UNIT = 1000
FIELD_NAMES = ("execution time", "period", "deadline")

@dataclass(frozen=True)
class Task:
    # One periodic task with all time values stored as integer ticks

    task_id: int
    execution_time: int
    period: int
    deadline: int

@dataclass
class Job:
    # One released instance of a periodic task

    task: Task
    release_time: int 
    absolute_deadline: int
    remaining_time: int

def parse_time(value: str, line_number: int, field_name: str) -> int:
    # Convert a positive decimal time value into exact 0.001 unit ticks

    try:
        number = Decimal(value) # (Decimal prevents binary floating point rounding before scaling)
    except InvalidOperation as exc:
        raise ValueError(
            f"line {line_number}: invalid {field_name} {value!r}"
        ) from exc

    if not number.is_finite() or number <= 0:
        raise ValueError(
            f"line {line_number}: {field_name} must be a positive number"
        )

    ticks = number * TICKS_PER_TIME_UNIT
    if ticks != ticks.to_integral_value():
        raise ValueError(
            f"line {line_number}: {field_name} has precision finer than 0.001"
        )

    return int(ticks)

def load_tasks(filename: str) -> list[Task]:
    # Read tasks from workload file in input order
    
    tasks: list[Task] = []

    requested_path = Path(filename)

    if requested_path.is_file():
        path = requested_path
    else:
        path = (
            Path(__file__).resolve().parent
            / "ece_455_final_exam_extra_files"
            / requested_path.name
        )

    try: 
        workload = path.open("r", encoding="utf-8-sig")
    except OSError as exc:
        raise ValueError(f"could not open {filename!r}: {exc}") from exc

    with workload:
        # File order defines task IDs and breaks equal period prority ties
        for line_number, raw_line in enumerate(workload, start=1):
            line = raw_line.strip()
            if not line:
                continue

            values = [value.strip() for value in line.split(",")]
            if len(values) != 3:
                raise ValueError(
                    f"line {line_number}: expected execution,period,deadline"
                )

            execution_time, period, deadline = (
                parse_time(value, line_number, field_name)
                for value, field_name in zip(values, FIELD_NAMES)
            )

            tasks.append(
                Task(
                    task_id=len(tasks),
                    execution_time=execution_time,
                    period=period,
                    deadline=deadline,
                )
            )

    if not tasks:
        raise ValueError("workload file contains no tasks")

    return tasks

def find_hyperperiod(tasks: Sequence[Task]) -> int:
    # Return the least common multiple of all task periods in ticks

    hyperperiod = 1
    for task in tasks:
        # lcm(a, b) = a * b / gcd(a, b) one period at a time
        hyperperiod = hyperperiod * task.period // gcd(
            hyperperiod, task.period
        )

    return hyperperiod

def release_jobs(tasks: Sequence[Task], current_time: int) -> list[Job]:
    # Create job instances for every task released at current time

    released_jobs: list[Job] = []
    for task in tasks:
        # Every task first releases at time zero, then once per period
        if current_time % task.period == 0:
            released_jobs.append(
                Job(
                    task=task,
                    release_time=current_time,
                    absolute_deadline=current_time + task.deadline,
                    remaining_time=task.execution_time,
                )
            )

    return released_jobs

def rm_priority_key(job: Job) -> tuple[int, int, int]:
    # Order jobs by period, input task order, then release time

    return job.task.period, job.task.task_id, job.release_time

def simulate_rm_schedule(tasks: Sequence[Task]) -> tuple[bool, list[int]]:
    # Simulate one hyperperiod using preemptive Rate Monotonic scheduling

    hyperperiod = find_hyperperiod(tasks)
    preemptions = [0] * len(tasks)
    ready_jobs: list[Job] = []
    running_job: Job | None = None
    current_time = 0

    while current_time < hyperperiod:
        # An unfinished job at its deadline makes the schedule infeasible
        for job in ready_jobs:
            if job.absolute_deadline <= current_time:
                return False, preemptions

        # Release new jobs, then select the highest fixed-priority ready job
        ready_jobs.extend(release_jobs(tasks, current_time))
        ready_jobs.sort(key=rm_priority_key)
        selected_job = ready_jobs[0] if ready_jobs else None

        # A switch away from an unfinished running job is one preemption
        if running_job is not None and selected_job is not running_job:
            preemptions[running_job.task.task_id] += 1

        running_job = selected_job
        next_release = min(
            (current_time // task.period + 1) * task.period
            for task in tasks
        )

        if running_job is None:
            current_time = min(next_release, hyperperiod)
            continue

        next_deadline = min(job.absolute_deadline for job in ready_jobs)
        completion_time = current_time + running_job.remaining_time

        # Jump directly to the next event instead of advancing tick by tick
        next_event = min(
            next_release,
            next_deadline,
            completion_time,
            hyperperiod,
        )

        # Give the selected job all processor time until that event
        running_job.remaining_time -= next_event - current_time
        current_time = next_event

        if running_job.remaining_time == 0:
            ready_jobs.remove(running_job)
            running_job = None

    # No unfinished work may carry into the repeated hyperperiod
    if ready_jobs:
        return False, preemptions

    return True, preemptions

def main(argv: Sequence[str] | None = None) -> int:
    # Main function call with argument

    arguments = sys.argv if argv is None else argv
    if len(arguments) != 2:
        program = Path(arguments[0]).name if arguments else "ece_455_final.py"
        print(f"Usage: python3 {program} <workload_file>", file=sys.stderr)
        return 2

    try:
        tasks = load_tasks(arguments[1])
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    schedulable, preemptions = simulate_rm_schedule(tasks)

    if schedulable: 
        print("1")
        print(",".join(str(count) for count in preemptions))
    else:
        print("0")
        print()

    return 0

if __name__ == "__main__":
    raise SystemExit(main())