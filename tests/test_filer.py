import pytest

from conftest import ac, docker


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
