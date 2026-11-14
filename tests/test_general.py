from conftest import INBOX, LIBRARY, ac, docker

ALBUM = dict(title="First Song", artist="Artist One", album_artist="Artist One", album="Solo Album", date="2020", track="1/2", disc="1/1")
SECOND = dict(ALBUM, title="Second Song", track="2/2")

# The environment variables each service may carry. A new one has to be added here on purpose, which is
# the moment to check that it holds no secret.
ALLOWED_ENVIRONMENT = {
    "metube": {"PUID", "PGID", "DOWNLOAD_DIR", "AUDIO_DOWNLOAD_DIR", "STATE_DIR", "TEMP_DIR", "OUTPUT_TEMPLATE", "YTDL_OPTIONS"},
    "music": set(),
    "beets-flask": {"TZ", "USER_ID", "GROUP_ID"},
}


@ac(1)
def test_the_beets_database_is_rebuilt_from_the_files(library):
    library.make_track("src/A", "1.m4a", **ALBUM)
    library.make_track("src/A", "2.m4a", **SECOND)
    listing = "$artist|$album|$title|$track|$year"

    library.beet("import", "-q", "-A", "-C", "-W", "/music/src/A")
    before = sorted(library.beet("ls", "-f", listing).splitlines())
    assert len(before) == 2

    docker("-c", "rm -f /data/*", mounts=library.mounts, entrypoint="sh")
    library.beet("import", "-q", "-A", "-C", "-W", "/music/src/A")
    assert sorted(library.beet("ls", "-f", listing).splitlines()) == before


@ac(2)
def test_no_container_carries_an_environment_variable_that_is_not_known_to_be_plain(compose):
    # A check against the values in 1Password needs the vault, which CI cannot reach, so this test guards
    # the place a secret would be put: the compose environment.
    for name, service in compose["services"].items():
        assert set(service.get("environment", {})) <= ALLOWED_ENVIRONMENT[name], name


@ac(4)
def test_only_the_inbox_and_the_library_are_mounted_into_more_than_one_service(compose):
    services_by_path = {}
    for name, service in compose["services"].items():
        for volume in service.get("volumes", []):
            services_by_path.setdefault(volume["source"], set()).add(name)
    shared = {path for path, services in services_by_path.items() if len(services) > 1}
    assert shared <= {INBOX, LIBRARY}
