#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["truenas_api_client @ git+https://github.com/truenas/api_client.git@TS-25.04.2.6"]
# ///
"""Deploy compose.yaml to the music-library TrueNAS app, with a snapshot first and a rollback if the app does not come up.

Usage: deploy.py <version> [--health URL ...] [--health-timeout SECONDS]

Reads TRUENAS_URL, TRUENAS_USERNAME and TRUENAS_API_KEY from the environment and compose.yaml from the repository root.
The two images this repo builds are pinned to <version> in what is sent, so the previous deploy's config is a rollback target.

A snapshot of the databases' dataset is taken before anything changes, and the deploy stops there when it fails. When the
app is not healthy after the redeploy, the app is stopped, the dataset is rolled back to the snapshot, the previous config
is applied and the app is redeployed.

Prints one JSON report on stdout. Exit code 0 means deployed, 1 means the deploy failed (aborted or rolled back) and 2 a usage error.
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.request

APP = "music-library"
DATASET = "Storage/Configuration/music-library"
IMAGES = ["ghcr.io/rn-ax/music-library", "ghcr.io/rn-ax/music-library-beets-flask"]
SERVICES = {"metube", "music", "beets-flask"}
HEALTH_PORTS = [30881, 30837, 30501]
KEEP_SNAPSHOTS = 10


def snapshot_name(now: datetime.datetime) -> str:
    return f"deploy-{now:%Y%m%dT%H%M%SZ}"


def pin_images(compose: str, version: str) -> str:
    """Replace the `latest` tag of each image this repo builds with the version being deployed."""
    for image in IMAGES:
        old = f"{image}:latest"
        if compose.count(old) != 1:
            raise ValueError(f"expected exactly one {old} in compose.yaml")
        compose = compose.replace(old, f"{image}:{version}")
    return compose


def host_of(url: str) -> str:
    return url.split("://")[-1].split("/")[0].split(":")[0]


class TrueNAS:
    def __init__(self, url: str, username: str, api_key: str):
        from truenas_api_client import Client

        socket = url.rstrip("/").replace("http://", "wss://").replace("https://", "wss://") + "/api/current"
        self.client = Client(uri=socket, verify_ssl=False)
        self.client.call("auth.login_ex", {"mechanism": "API_KEY_PLAIN", "username": username, "api_key": api_key})

    def call(self, method, *args):
        return self.client.call(method, *args)

    def job(self, method, *args, timeout=900):
        job = self.client.call(method, *args, job="RETURN")
        if not job.event.wait(timeout=timeout):
            raise TimeoutError(f"{method} did not finish within {timeout} seconds")
        return job.result()


def healthy(truenas: TrueNAS, urls: list[str]) -> bool:
    apps = truenas.call("app.query", [["name", "=", APP]])
    if not apps or apps[0]["state"] != "RUNNING":
        return False
    containers = {c["service_name"]: c["state"] for c in apps[0]["active_workloads"]["container_details"]}
    if set(containers) != SERVICES or set(containers.values()) != {"running"}:
        return False
    for url in urls:
        try:
            if urllib.request.urlopen(url, timeout=10).status != 200:
                return False
        except OSError:
            return False
    return True


def wait_until_healthy(truenas: TrueNAS, urls: list[str], timeout: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if healthy(truenas, urls):
            return True
        time.sleep(10)
    return False


def pull_images(truenas: TrueNAS, version: str) -> None:
    registry = next(r for r in truenas.call("app.registry.query") if "ghcr.io" in r["uri"])
    auth = {"username": registry["username"], "password": registry["password"], "registry_uri": "ghcr.io"}
    for image in IMAGES:
        truenas.job("app.image.pull", {"image": f"{image}:{version}", "auth_config": auth})


def prune_snapshots(truenas: TrueNAS) -> int:
    snapshots = truenas.call("zfs.snapshot.query", [["dataset", "=", DATASET], ["snapshot_name", "^", "deploy-"]], {"order_by": ["snapshot_name"]})
    old = snapshots[:-KEEP_SNAPSHOTS]
    for snapshot in old:
        truenas.call("zfs.snapshot.delete", snapshot["id"])
    return len(old)


def deploy(truenas: TrueNAS, version: str, compose: str, urls: list[str], timeout: int, report: dict) -> bool:
    steps = report["steps"]
    pinned = pin_images(compose, version)
    previous = truenas.call("app.config", APP)

    name = snapshot_name(datetime.datetime.now(datetime.timezone.utc))
    truenas.call("zfs.snapshot.create", {"dataset": DATASET, "name": name})
    snapshot = f"{DATASET}@{name}"
    report["snapshot"] = snapshot
    steps.append("snapshot")

    pull_images(truenas, version)
    steps.append("pull")
    truenas.job("app.update", APP, {"custom_compose_config_string": pinned})
    truenas.job("app.redeploy", APP)
    steps.append("redeploy")

    if wait_until_healthy(truenas, urls, timeout):
        steps.append("healthy")
        report["pruned"] = prune_snapshots(truenas)
        return True

    steps.append("unhealthy")
    truenas.job("app.stop", APP)
    truenas.call("zfs.snapshot.rollback", snapshot, {"force": True, "recursive": True})
    truenas.job("app.update", APP, {"custom_compose_config": previous})
    truenas.job("app.redeploy", APP)
    steps.append("rolled back")
    report["healthy_after_rollback"] = wait_until_healthy(truenas, urls, timeout)
    return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Deploy compose.yaml to the music-library TrueNAS app.")
    parser.add_argument("version")
    parser.add_argument("--health", action="append", help="URL that must answer 200 after the deploy; defaults to the three service ports")
    parser.add_argument("--health-timeout", type=int, default=300)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    report = {"script": "deploy", "version": args.version, "steps": []}
    code = 1
    try:
        url = os.environ["TRUENAS_URL"]
        urls = args.health or [f"http://{host_of(url)}:{port}/" for port in HEALTH_PORTS]
        truenas = TrueNAS(url, os.environ["TRUENAS_USERNAME"], os.environ["TRUENAS_API_KEY"])
        compose = (pathlib.Path(__file__).resolve().parent.parent / "compose.yaml").read_text()
        code = 0 if deploy(truenas, args.version, compose, urls, args.health_timeout, report) else 1
        report["result"] = "deployed" if code == 0 else "rolled back"
    except Exception as e:
        report["error"] = {"step": report["steps"][-1] if report["steps"] else "start", "type": type(e).__name__, "message": str(e)}
        report["result"] = "aborted" if "redeploy" not in report["steps"] else "failed"
    finally:
        print(json.dumps(report))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
