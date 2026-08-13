from __future__ import annotations 

import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

TICKS_PER_TIME_UNIT = 1000
FIELD_NAMES = ("execution time", "period", "deadline")

@dataclass(frozen=True)
class Task:
    # One periodic task with all time values stored as integer ticks

    task_id: int
    execution_time: int
    period: int
    deadline: int

def parse_time(value: str, line_number: int, field_name: str) -> int:
    # Convert a positive decimal time value into exact 0.001 unit ticks

    try:
        number = Decimal(value)
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
    path = (
        Path(__file__).resolve().parent
        / "ece_455_final_exam_extra_files"
        / Path(filename).name
    )

    try: 
        workload = path.open("r", encoding="utf-8-sig")
    except OSError as exc:
        raise ValueError(f"could not open {filename!r}: {exc}") from exc

    with workload:
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

    # Placeholder tasks
    _ = tasks
    return 0

if __name__ == "__main__":
    raise SystemExit(main())