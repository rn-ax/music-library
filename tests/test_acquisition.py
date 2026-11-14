import shutil

from conftest import INBOX, ac

METUBE_STATE = "/mnt/Storage/Configuration/music-library/metube"


@ac(9)
def test_metube_mounts_only_the_inbox_and_its_own_state(compose):
    mounted = {volume["source"] for volume in compose["services"]["metube"]["volumes"]}
    assert mounted == {INBOX, METUBE_STATE}


@ac(31)
def test_a_download_submitted_without_a_format_is_m4a_audio(metube):
    url = metube.make_video("clip.mp4")

    metube.add(url)
    metube.wait(lambda: metube.downloaded(), "a download to finish")

    assert metube.downloaded() == ["clip/clip.m4a"]
    assert metube.stream_types("clip/clip.m4a") == ["audio"]


@ac(32)
def test_a_download_uses_the_highest_bitrate_aac_stream_the_source_offers(metube):
    url = metube.make_dash_audio(bitrates=(64, 192, 128))

    metube.add(url)
    metube.wait(lambda: metube.downloaded(), "a download to finish")

    [downloaded] = metube.downloaded()
    assert downloaded.endswith(".m4a")
    assert metube.bitrate(downloaded) > 160_000


@ac(33)
def test_audio_that_was_already_downloaded_is_not_downloaded_again(metube):
    url = metube.make_video("clip.mp4")
    metube.add(url)
    metube.wait(lambda: metube.downloaded(), "the first download to finish")
    shutil.rmtree(metube.inbox / "clip")
    assert metube.downloaded() == []

    metube.add(url)
    metube.wait(metube.idle, "MeTube to finish with the second submission")

    assert metube.downloaded() == []
