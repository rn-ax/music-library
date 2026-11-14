import json
import os
import pathlib
import shutil
import subprocess
import time
import urllib.request
import uuid

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMAGE = os.environ.get("IMAGE", "music-library:ci")
BEETS_FLASK_IMAGE = os.environ.get("BEETS_FLASK_IMAGE", "music-library-beets-flask:ci")
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


class MeTube:
    """The metube service from compose.yaml, run against scratch directories and a local media server."""

    def __init__(self, tmp_path: pathlib.Path, service: dict):
        self.name = f"ac-{uuid.uuid4().hex[:8]}"
        self.inbox = tmp_path / "inbox"
        self.state = tmp_path / "state"
        self.media = tmp_path / "media"
        for directory in (self.inbox, self.state, self.media):
            directory.mkdir()
        user = f"{os.getuid()}:{os.getgid()}"
        self.run("docker", "network", "create", self.name)
        self.run(
            "docker", "run", "-d", "--rm", "--name", f"{self.name}-media", "--network", self.name, "--platform", "linux/amd64",
            "--user", user, "-v", f"{self.media}:/srv", "--entrypoint", "python", IMAGE, "-m", "http.server", "8000", "--directory", "/srv",
        )
        environment = dict(service["environment"], PUID=str(os.getuid()), PGID=str(os.getgid()), ALLOW_PRIVATE_ADDRESSES="true")
        self.run(
            "docker", "run", "-d", "--rm", "--name", f"{self.name}-metube", "--network", self.name, "--platform", "linux/amd64",
            "-p", "127.0.0.1::8081", "-v", f"{self.inbox}:/downloads", "-v", f"{self.state}:/state",
            *[arg for key, value in environment.items() for arg in ("-e", f"{key}={value}")], service["image"],
        )
        self.port = self.run("docker", "port", f"{self.name}-metube", "8081/tcp").split(":")[-1].strip()
        self.wait(lambda: self.get("/") is not None, "MeTube to answer")

    @staticmethod
    def run(*cmd):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise AssertionError(f"{' '.join(cmd)}\n{result.stdout}\n{result.stderr}")
        return result.stdout

    def get(self, path):
        try:
            return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5).read()
        except OSError:
            return None

    def wait(self, condition, what, timeout=180):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition():
                return
            time.sleep(2)
        logs = subprocess.run(["docker", "logs", "--tail", "30", f"{self.name}-metube"], capture_output=True, text=True)
        raise AssertionError(f"timed out waiting for {what}\n{logs.stdout}{logs.stderr}")

    def make_video(self, name: str):
        """A two second clip with a picture and an AAC soundtrack, served by the local media server."""
        docker(
            "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=64x64:rate=5", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", f"/srv/{name}", mounts=[(self.media, "/srv")], entrypoint="ffmpeg",
        )
        return f"http://{self.name}-media:8000/{name}"

    def make_clip(self, name: str, kbps: int):
        """A six second clip with a picture and an AAC soundtrack at a constant bitrate, served by the local media server."""
        docker(
            "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=6:size=64x64:rate=5", "-f", "lavfi", "-i", "anoisesrc=duration=6:color=pink:sample_rate=44100",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", f"{kbps}k", "-shortest", f"/srv/{name}", mounts=[(self.media, "/srv")], entrypoint="ffmpeg",
        )
        return f"http://{self.name}-media:8000/{name}"

    def source_bitrate(self, name: str) -> int:
        out = docker("-v", "error", "-select_streams", "a:0", "-show_entries", "stream=bit_rate", "-of", "csv=p=0", f"/srv/{name}", mounts=[(self.media, "/srv")], entrypoint="ffprobe")
        return int(out.strip())

    def make_dash_audio(self, bitrates=(64, 192, 128)):
        """A DASH manifest with one AAC audio stream per bitrate (kbit/s), served by the local media server."""
        streams = [arg for _ in bitrates for arg in ("-map", "0:a")]
        rates = [arg for index, kbps in enumerate(bitrates) for arg in (f"-b:a:{index}", f"{kbps}k")]
        (self.media / "dash").mkdir()
        docker(
            "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=duration=6:color=pink:sample_rate=44100", *streams, "-c:a", "aac", *rates,
            "-f", "dash", "-seg_duration", "2", "-use_timeline", "1", "-use_template", "1", "/srv/dash/manifest.mpd",
            mounts=[(self.media, "/srv")], entrypoint="ffmpeg",
        )
        return f"http://{self.name}-media:8000/dash/manifest.mpd"

    def codec(self, path: str) -> str:
        out = docker("-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0", f"/inbox/{path}", mounts=[(self.inbox, "/inbox")], entrypoint="ffprobe")
        return out.strip()

    def bitrate(self, path: str) -> int:
        out = docker("-v", "error", "-select_streams", "a:0", "-show_entries", "stream=bit_rate", "-of", "csv=p=0", f"/inbox/{path}", mounts=[(self.inbox, "/inbox")], entrypoint="ffprobe")
        return int(out.strip())

    def add(self, url: str, **options):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/add", data=json.dumps({"url": url, **options}).encode(),
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(request, timeout=30).read())

    def idle(self) -> bool:
        """True when MeTube has nothing queued or pending."""
        history = self.get("/history")
        if history is None:
            return False
        data = json.loads(history)
        return not data.get("queue") and not data.get("pending")

    def files(self) -> list[str]:
        return sorted(str(p.relative_to(self.inbox)) for p in self.inbox.rglob("*") if p.is_file() and ".part" not in p.name)

    def downloaded(self) -> list[str]:
        return sorted(str(p.relative_to(self.inbox)) for p in self.inbox.rglob("*") if p.is_file() and not p.name.endswith(".json") and ".part" not in p.name)

    def stream_types(self, path: str) -> list[str]:
        out = docker("-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", f"/inbox/{path}", mounts=[(self.inbox, "/inbox")], entrypoint="ffprobe")
        return out.split()

    def close(self):
        for name in (f"{self.name}-metube", f"{self.name}-media"):
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
        subprocess.run(["docker", "network", "rm", self.name], capture_output=True)


@pytest.fixture
def metube(tmp_path, compose):
    server = MeTube(tmp_path, compose["services"]["metube"])
    yield server
    server.close()


PREVIEWED = 3  # beets-flask's FolderStatus: candidates fetched, waiting for a person


class BeetsFlask:
    """The beets-flask service run with the repo's seed configuration against scratch directories."""

    def __init__(self, tmp_path: pathlib.Path):
        self.name = f"ac-{uuid.uuid4().hex[:8]}"
        self.config, self.music, self.inbox = tmp_path / "config", tmp_path / "music", tmp_path / "inbox"
        for directory in (self.config / "beets", self.config / "beets-flask", self.music, self.inbox):
            directory.mkdir(parents=True)
        shutil.copy(ROOT / "beets-flask" / "beets.yaml", self.config / "beets" / "config.yaml")
        shutil.copy(ROOT / "beets-flask" / "config.yaml", self.config / "beets-flask" / "config.yaml")
        self.inbox_mounts = [(self.inbox, "/inbox")]
        subprocess.run(
            [
                "docker", "run", "-d", "--rm", "--name", self.name, "--platform", "linux/amd64", "-p", "127.0.0.1::5001",
                "-e", "TZ=UTC", "-e", f"USER_ID={os.getuid()}", "-e", f"GROUP_ID={os.getgid()}",
                "-v", f"{self.config}:/config", "-v", f"{self.music}:/music", "-v", f"{self.inbox}:/inbox", BEETS_FLASK_IMAGE,
            ],
            capture_output=True, text=True, check=True,
        )
        self.port = subprocess.run(["docker", "port", self.name, "5001/tcp"], capture_output=True, text=True, check=True).stdout.split(":")[-1].strip()
        self.wait(lambda: self.get("/") is not None, "beets-flask to answer", timeout=300)

    def get(self, path):
        try:
            return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5).read()
        except OSError:
            return None

    def wait(self, condition, what, timeout=120):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition():
                return
            time.sleep(1)
        logs = subprocess.run(["docker", "logs", "--tail", "30", self.name], capture_output=True, text=True)
        raise AssertionError(f"timed out waiting for {what}\n{logs.stdout}{logs.stderr}")

    def add_album(self, folder: str, title: str):
        """A folder in the inbox holding one short tagged AAC track."""
        (self.inbox / folder).mkdir()
        docker(
            "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=duration=2:color=pink", "-c:a", "aac",
            "-metadata", f"title={title}", "-metadata", "artist=Test Artist", f"/inbox/{folder}/track.m4a",
            mounts=self.inbox_mounts, entrypoint="ffmpeg",
        )

    def folders(self) -> set[str]:
        """The folders directly inside the inbox that beets-flask lists."""
        body = self.get("/api_v1/inbox/tree")
        if body is None:
            return set()
        return {child["full_path"] for root in json.loads(body) for child in root.get("children", []) if child["type"] == "directory"}

    def statuses(self) -> dict[str, int]:
        body = self.get("/api_v1/session/status")
        return {} if body is None else {item["path"]: item["status"] for item in json.loads(body)}

    def close(self):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)


@pytest.fixture
def beets_flask(tmp_path):
    server = BeetsFlask(tmp_path)
    yield server
    server.close()
