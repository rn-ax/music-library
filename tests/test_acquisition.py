from conftest import INBOX, ac

METUBE_STATE = "/mnt/Storage/Configuration/music-library/metube"


@ac(9)
def test_metube_mounts_only_the_inbox_and_its_own_state(compose):
    mounted = {volume["source"] for volume in compose["services"]["metube"]["volumes"]}
    assert mounted == {INBOX, METUBE_STATE}
