import datetime
import importlib.util
import pathlib

import pytest

spec = importlib.util.spec_from_file_location("deploy", pathlib.Path(__file__).resolve().parent.parent / "scripts" / "deploy.py")
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)

COMPOSE = (pathlib.Path(__file__).resolve().parent.parent / "compose.yaml").read_text()


def test_pinning_replaces_the_latest_tag_of_both_images_this_repo_builds():
    pinned = deploy.pin_images(COMPOSE, "2026.11.14.7")

    assert "ghcr.io/rn-ax/music-library:2026.11.14.7" in pinned
    assert "ghcr.io/rn-ax/music-library-beets-flask:2026.11.14.7" in pinned
    assert ":latest" not in pinned
    assert "ghcr.io/alexta69/metube:2026.10.27" in pinned


def test_pinning_fails_when_an_image_is_missing_from_the_compose_file():
    with pytest.raises(ValueError):
        deploy.pin_images("services: {}", "2026.11.14.7")


def test_a_snapshot_name_ends_in_a_utc_timestamp():
    now = datetime.datetime(2026, 11, 14, 19, 8, 1, tzinfo=datetime.timezone.utc)
    assert deploy.snapshot_name(now) == "deploy-20261114T190801Z"


def test_the_host_is_read_from_the_truenas_url():
    assert deploy.host_of("http://truenas.machine.rn.ax") == "truenas.machine.rn.ax"
    assert deploy.host_of("https://truenas.lan:8443/api") == "truenas.lan"
