import os

from wheelsproxy import models


def test_upload_external_build_to():
    instance = models.ExternalBuild(
        external_url='http://example.com',
        platform=models.Platform(slug='test')
    )
    filename = 'my-package.whl'
    path = models.upload_external_build_to(instance, filename)

    assert path.startswith('__external__')

    # The filename has to be preserved in order for pip to correctly
    # detect the wheel compatibility
    assert os.path.basename(path) == filename


def test_ordering_same_normalized_version():
    releases = [
        models.Release(version='1.0'),
        models.Release(version='2'),
        models.Release(version='2.0'),
    ]

    sorting_tuple = [
        (rel.parsed_version, rel)
        for rel in releases
    ]

    assert sorted(sorting_tuple, key=lambda t: t[0]) == sorting_tuple
