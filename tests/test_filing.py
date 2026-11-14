from conftest import PREVIEWED, ac, docker

AC_ALBUM = dict(artist="Artist One", album_artist="Artist One", album="Solo Album", date="2020", disc="1/1")


def import_and_file(library, folder, *flags):
    """Import a folder as it is, then file it by the path templates."""
    library.beet("import", "-q", "-A", "-C", "-W", *flags, f"/music/{folder}")
    library.beet("move")


def keeps_its_audio_stream(library, codec):
    track = library.make_track("src/A", "1.m4a", codec=codec, title="First Song", track="1/1", **AC_ALBUM)
    before = library.audio_md5("/music/src/A/1.m4a")

    library.beet("import", "-q", "-A", "-C", "-m", "-w", "/music/src/A")

    assert not track.exists()
    assert library.audio_md5("/music/Artist One/Solo Album (2020)/01 First Song.m4a") == before


@ac(12)
def test_an_imported_aac_file_keeps_its_audio_stream(library):
    keeps_its_audio_stream(library, "aac")


@ac(12)
def test_an_imported_alac_file_keeps_its_audio_stream(library):
    keeps_its_audio_stream(library, "alac")


@ac(13)
def test_an_album_track_is_filed_under_its_album_artist_and_album(library):
    library.make_track("src/A", "1.m4a", title="First Song", track="1/2", **AC_ALBUM)
    library.make_track("src/A", "2.m4a", title="Second Song", track="2/2", **AC_ALBUM)

    import_and_file(library, "src/A")

    assert library.files() == [
        "Artist One/Solo Album (2020)/01 First Song.m4a",
        "Artist One/Solo Album (2020)/02 Second Song.m4a",
    ]


@ac(14)
def test_a_track_of_a_multi_disc_album_has_its_disc_number_before_its_track_number(library):
    two_discs = dict(artist="Artist Two", album_artist="Artist Two", album="Double Album", date="2021", track="1/1")
    library.make_track("src/B", "1.m4a", title="Disc One Opener", disc="1/2", **two_discs)
    library.make_track("src/B", "2.m4a", title="Disc Two Opener", disc="2/2", **two_discs)

    import_and_file(library, "src/B")

    assert library.files() == [
        "Artist Two/Double Album (2021)/01-01 Disc One Opener.m4a",
        "Artist Two/Double Album (2021)/02-01 Disc Two Opener.m4a",
    ]


@ac(15)
def test_a_compilation_track_is_filed_under_compilations_with_its_own_artist(library):
    compilation = dict(album_artist="Various Artists", album="Hits", date="2019", disc="1/1")
    library.make_track("src/C", "1.m4a", title="Hit One", artist="Band X", track="1/2", **compilation)
    library.make_track("src/C", "2.m4a", title="Hit Two", artist="Band Y", track="2/2", **compilation)

    library.beet("import", "-q", "-A", "-C", "-W", "/music/src/C")
    library.beet("modify", "-y", "-a", "album:Hits", "comp=1")
    library.beet("move")

    assert library.files() == [
        "Compilations/Hits (2019)/01 Band X - Hit One.m4a",
        "Compilations/Hits (2019)/02 Band Y - Hit Two.m4a",
    ]


@ac(16)
def test_a_single_is_filed_directly_under_its_artist(library):
    library.make_track("src/D", "s.m4a", title="Lonely Song", artist="Solo Singer")

    import_and_file(library, "src/D", "-s")

    assert library.files() == ["Solo Singer/Lonely Song.m4a"]


@ac(17)
def test_an_import_without_flags_changes_no_file(library):
    library.make_track("src/A", "1.m4a", title="First Song", track="1/1", **AC_ALBUM)
    before = {name: library.audio_md5(f"/music/{name}") for name in library.files()}
    mtimes = {name: (library.music / name).stat().st_mtime_ns for name in library.files()}

    library.beet("import", "-q", "-A", "/music/src/A")

    assert library.files() == sorted(before)
    assert {name: library.audio_md5(f"/music/{name}") for name in library.files()} == before
    assert {name: (library.music / name).stat().st_mtime_ns for name in library.files()} == mtimes


@ac(18)
def test_beet_update_reads_a_tag_changed_directly_in_a_file(library):
    library.make_track("src/A", "1.m4a", title="First Song", track="1/1", **AC_ALBUM)
    library.beet("import", "-q", "-A", "-C", "-W", "/music/src/A")

    docker(
        "-c", "from mutagen.mp4 import MP4; f = MP4('/music/src/A/1.m4a'); f['\\xa9nam'] = ['Changed Title']; f.save()",
        mounts=library.mounts, entrypoint="python",
    )
    assert library.beet("ls", "-f", "$title").strip() == "First Song"

    library.beet("update")

    assert library.beet("ls", "-f", "$title").strip() == "Changed Title"


@ac(35)
def test_every_folder_in_the_inbox_appears_for_review_within_a_minute(beets_flask):
    beets_flask.add_album("abc123", "First Song")
    beets_flask.add_album("def456", "Second Song")
    expected = {"/inbox/abc123", "/inbox/def456"}

    beets_flask.wait(
        lambda: expected <= beets_flask.folders() and all(beets_flask.statuses().get(path) == PREVIEWED for path in expected),
        "both folders to be previewed for review",
        timeout=60,
    )
