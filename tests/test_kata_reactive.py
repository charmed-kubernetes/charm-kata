from reactive import kata


def test_packages_list():
    """Assert KATA_PACKAGES is a list of strings."""
    assert isinstance(kata.KATA_PACKAGES, list)
    for item in kata.KATA_PACKAGES:
        assert isinstance(item, str)


def test_install_kata():
    """Assert install_kata is a method."""
    assert callable(kata.install_kata)


def test_purge_kata():
    """Assert purge_kata is a method."""
    assert callable(kata.purge_kata)


def test_publist_config():
    """Assert publish_config is a method."""
    assert callable(kata.publish_config)


def test_series_upgrade():
    """Assert status is set during series upgrade."""
    assert kata.status.blocked.call_count == 0
    assert kata.status.active.call_count == 0
    kata.pre_series_upgrade()
    assert kata.status.blocked.call_count == 1
    assert kata.status.active.call_count == 0
    kata.post_series_upgrade()
    assert kata.status.blocked.call_count == 1
    assert kata.status.active.call_count == 1
