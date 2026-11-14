import json
import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGE = os.environ.get("IMAGE", "music-library:ci")
INBOX = "/mnt/Storage/Downloads/metube"
LIBRARY = "/mnt/Storage/Music"


def ac(n):
    """Mark a test as checking acceptance criterion AC-<n>, which puts [AC-<n>] in the test's id."""

    def decorate(fn):
        fn = pytest.mark.usefixtures("ac_id")(fn)
        return pytest.mark.parametrize("ac_id", [pytest.param(n, id=f"AC-{n}")])(fn)

    return decorate


@pytest.fixture
def ac_id():
    return None


def docker(*args, mounts=(), entrypoint=None, check=True):
    """Run the music image with the current user and the given host:container mounts."""
    cmd = ["docker", "run", "--rm", "--platform", "linux/amd64", "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]
    for host, container in mounts:
        cmd += ["-v", f"{host}:{container}"]
    if entrypoint:
        cmd += ["--entrypoint", entrypoint]
    cmd += [IMAGE, *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(f"{' '.join(cmd)}\n{result.stdout}\n{result.stderr}")
    return result.stdout


class Library:
    """A scratch library: /music and beets' /data inside the image, both on temporary host directories."""

    def __init__(self, base: pathlib.Path):
        self.music = base / "music"
        self.data = base / "data"
        self.music.mkdir()
        self.data.mkdir()

    @property
    def mounts(self):
        return [(self.music, "/music"), (self.data, "/data")]

    def beet(self, *args):
        return docker("-c", "/etc/beets/config.yaml", *args, mounts=self.mounts, entrypoint="beet")

    def make_track(self, folder: str, name: str, codec: str = "aac", **tags) -> pathlib.Path:
        """Create a short silent track in /music/<folder>, with the tags given as ffmpeg metadata keys."""
        (self.music / folder).mkdir(parents=True, exist_ok=True)
        metadata = [arg for key, value in tags.items() for arg in ("-metadata", f"{key}={value}")]
        docker(
            "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.3",
            "-c:a", codec, *metadata, f"/music/{folder}/{name}",
            mounts=self.mounts, entrypoint="ffmpeg",
        )
        return self.music / folder / name

    def audio_md5(self, path: str) -> str:
        return docker("-v", "error", "-i", path, "-map", "0:a:0", "-c", "copy", "-f", "md5", "-", mounts=self.mounts, entrypoint="ffmpeg").strip()

    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.music)) for p in self.music.rglob("*") if p.is_file())


@pytest.fixture
def library(tmp_path):
    return Library(tmp_path)


@pytest.fixture(scope="session")
def compose():
    out = subprocess.run(["docker", "compose", "config", "--format", "json"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return json.loads(out)
