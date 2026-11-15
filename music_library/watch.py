"""Run the filing script whenever something happens in the staging folder, on a timer and at start.

The watcher holds no logic of its own: an event, the timer or a start only runs the filing script, which looks at what is
waiting and files it. Events that arrive close together are merged into one run, and files that were still being written
when a run looked at them get another run as soon as they have settled. The runs are serial, so only one happens at a time.

Usage: python -m music_library.watch --staging DIR --library DIR [--settle SECONDS] [--interval SECONDS] [--quiet SECONDS]
Prints a JSON line for every run that filed, kept or failed something.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

from music_library import filer


def watch_events(staging: pathlib.Path, event: threading.Event) -> None:
    """Set the event for every file that finishes or is moved into place under the staging folder."""
    process = subprocess.Popen(
        ["inotifywait", "--monitor", "--recursive", "--quiet", "--event", "close_write,moved_to", "--format", "%w%f", str(staging)],
        stdout=subprocess.PIPE, text=True,
    )
    for _ in process.stdout:
        event.set()
    print(f"inotifywait stopped with exit code {process.wait()}", file=sys.stderr, flush=True)
    os._exit(1)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the filing script on file events, on a timer and at start.")
    parser.add_argument("--staging", type=pathlib.Path, required=True)
    parser.add_argument("--library", type=pathlib.Path, required=True)
    parser.add_argument("--settle", type=float, default=10, help="seconds a file must have been unchanged before it is filed")
    parser.add_argument("--interval", type=float, default=3600, help="seconds between runs when nothing happens")
    parser.add_argument("--quiet", type=float, default=2, help="seconds without events before a run starts")
    args = parser.parse_args(argv)

    event = threading.Event()
    threading.Thread(target=watch_events, args=(args.staging, event), daemon=True).start()

    wait = 0.0  # the first run is at start
    while True:
        event.wait(timeout=wait)
        while event.is_set():
            event.clear()
            time.sleep(args.quiet)
        report = filer.run(args.staging, args.library, args.settle)
        if any(report[key] for key in ("filed", "converted", "kept", "failed")):
            print(json.dumps({key: value for key, value in report.items() if value}), flush=True)
        wait = args.settle + 1 if report["waiting"] else args.interval


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
