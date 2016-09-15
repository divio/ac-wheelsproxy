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
