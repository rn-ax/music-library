import os
import subprocess
import time
import uuid

import pytest

from conftest import IMAGE, ac, docker


class Filer:
    """The filing script run in the music image against scratch staging and library folders."""

    def __init__(self, tmp_path):
        self.staging, self.library = tmp_path / "staging", tmp_path / "library"
        self.staging.mkdir()
        self.library.mkdir()
        self.mounts = [(self.staging, "/staging"), (self.library, "/library")]

    def make(self, relative: str, codec: str, **tags):
        """A short silent file at /staging/<relative>, encoded with the given ffmpeg codec and tagged."""
        (self.staging / relative).parent.mkdir(parents=True, exist_ok=True)
        metadata = [arg for key, value in tags.items() for arg in ("-metadata", f"{key}={value}")]
        docker(
            "-v", "error", "-y", "-f", "lavfi", "-i", "anoisesrc=duration=1:color=pink:sample_rate=44100", "-c:a", codec, *metadata,
            f"/staging/{relative}", mounts=self.mounts, entrypoint="ffmpeg",
        )

    def run(self):
        return docker("-m", "music_library.filer", "--staging", "/staging", "--library", "/library", "--settle", "0", mounts=self.mounts, entrypoint="python")

    def files(self, root) -> list[str]:
        return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())

    def probe(self, path: str, entry: str) -> str:
        return docker("-v", "error", "-select_streams", "a:0", "-show_entries", entry, "-of", "csv=p=0", f"/library/{path}", mounts=self.mounts, entrypoint="ffprobe").strip()


@pytest.fixture
def filer(tmp_path):
    return Filer(tmp_path)


@ac(36)
def test_an_aac_file_is_moved_into_the_library_as_it_is(filer):
    filer.make("Some Uploader/whatever.m4a", "aac", artist="Some Uploader", title="Some Song")

    filer.run()

    assert filer.files(filer.library) == ["Some Uploader/Some Song.m4a"]
    assert filer.files(filer.staging) == []
    assert filer.probe("Some Uploader/Some Song.m4a", "stream=codec_name") == "aac"


@ac(36)
def test_a_flac_file_is_converted_to_alac_and_moved_into_the_library(filer):
    filer.make("Lossless Artist/track.flac", "flac", artist="Lossless Artist", title="Lossless Song")

    filer.run()

    assert filer.files(filer.library) == ["Lossless Artist/Lossless Song.m4a"]
    assert filer.files(filer.staging) == []
    assert filer.probe("Lossless Artist/Lossless Song.m4a", "stream=codec_name") == "alac"
    assert filer.probe("Lossless Artist/Lossless Song.m4a", "format_tags=title") == "Lossless Song"


@ac(36)
def test_an_mp3_file_is_converted_to_aac_and_moved_into_the_library(filer):
    filer.make("Lossy Artist/track.mp3", "libmp3lame", artist="Lossy Artist", title="Lossy Song")

    filer.run()

    assert filer.files(filer.library) == ["Lossy Artist/Lossy Song.m4a"]
    assert filer.files(filer.staging) == []
    assert filer.probe("Lossy Artist/Lossy Song.m4a", "stream=codec_name") == "aac"


class Watcher:
    """The watcher service run in the music image against scratch staging and library folders."""

    def __init__(self, filer: Filer):
        self.filer = filer
        self.name = f"ac-{uuid.uuid4().hex[:8]}"
        subprocess.run(
            [
                "docker", "run", "-d", "--rm", "--name", self.name, "--platform", "linux/amd64", "--user", f"{os.getuid()}:{os.getgid()}",
                "-v", f"{filer.staging}:/staging", "-v", f"{filer.library}:/library", "--entrypoint", "python", IMAGE,
                "-m", "music_library.watch", "--staging", "/staging", "--library", "/library",
            ],
            capture_output=True, text=True, check=True,
        )

    def running(self) -> bool:
        out = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", self.name], capture_output=True, text=True)
        return out.stdout.strip() == "true"

    def logs(self) -> str:
        out = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True)
        return out.stdout + out.stderr

    def wait_for(self, condition, what: str, timeout: float):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if condition():
                return
            if not self.running():
                raise AssertionError(f"the watcher stopped while waiting for {what}\n{self.logs()}")
            time.sleep(2)
        raise AssertionError(f"timed out waiting for {what}\n{self.logs()}")

    def close(self):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)


@pytest.fixture
def watcher(filer):
    server = Watcher(filer)
    yield server
    server.close()


@ac(37)
def test_a_file_that_finishes_in_staging_reaches_the_library_without_anyone_starting_the_script(filer, watcher):
    watcher.wait_for(watcher.running, "the watcher to start", timeout=30)
    time.sleep(5)  # let it finish its first pass, so the file below arrives while it is only watching

    filer.make("Watched Artist/download.m4a", "aac", artist="Watched Artist", title="Watched Song")

    watcher.wait_for(lambda: filer.files(filer.library) == ["Watched Artist/Watched Song.m4a"], "the file to reach the library", timeout=120)
    assert filer.files(filer.staging) == []
