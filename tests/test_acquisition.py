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
