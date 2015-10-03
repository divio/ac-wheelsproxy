import os
import contextlib
from tempfile import mkdtemp
import shutil
import hashlib
import io

from six.moves import urllib, shlex_quote

from docker import Client, tls

from django.conf import settings
from django.core.files import File
from django.utils import timezone


@contextlib.contextmanager
def tempdir(*args, **kwargs):
    tmp_path = mkdtemp(*args, **kwargs)
    try:
        yield tmp_path
    finally:
        pass
    shutil.rmtree(tmp_path)


def get_docker_client(host, cert_path):
    tls_config = None
    url = urllib.parse.urlparse(host)
    if url.scheme in ['tcp', 'https']:
        host = 'https://{}'.format(url.netloc)
        if cert_path:
            cert = os.path.join(cert_path, 'cert.pem')
            key = os.path.join(cert_path, 'key.pem')
            ca = os.path.join(cert_path, 'ca.pem')
            tls_config = tls.TLSConfig(
                client_cert=(cert, key),
                verify=ca,
                assert_hostname=False,
            )
    return Client(host, tls=tls_config, version='auto')


def file_digest(algorithm, fh, chunk_size=4096):
    hash = algorithm()
    for chunk in iter(lambda: fh.read(chunk_size), ''):
        hash.update(chunk)
    return hash.hexdigest()


class DockerBuilder(object):
    def __init__(self, platform_spec):
        self.image = platform_spec['image']
        self.client = get_docker_client(
            settings.DOCKER_BUILDER_ENDPOINT,
            settings.DOCKER_BUILDER_CERTS,
        )

    def __call__(self, build):
        cmd = ' '.join([
            'pip', 'wheel',
            '--no-deps',
            '--no-clean',
            '--no-index',
            shlex_quote(build.original_url),
        ])

        with tempdir(dir=settings.TEMP_BUILD_ROOT) as wheelhouse:
            container = self.client.create_container(
                self.image,
                cmd,
                working_dir='/',
                volumes=['/wheelhouse'],
                host_config=self.client.create_host_config(binds={
                    wheelhouse: {
                        'bind': '/wheelhouse',
                        'ro': False,
                    }
                }),
            )

            build_start = timezone.now()
            self.client.start(container=container['Id'])
            build_log = io.StringIO()
            for s in self.client.attach(container=container['Id'],
                                        stdout=True, stderr=True, stream=True):
                build_log.write(s.decode('utf8'))
            build_duration = timezone.now() - build_start

            filenames = os.listdir(wheelhouse)
            assert len(filenames) == 1
            filename = filenames[0]
            with open(os.path.join(wheelhouse, filename), 'rb') as fh:
                digest = file_digest(hashlib.md5, fh)
                build.build.save(filename, File(fh))

        build.build_duration = build_duration.seconds
        build.build_log = build_log.getvalue()
        build.build_timestamp = timezone.now()
        build.md5_digest = digest
        build.filesize = build.build.size
        build.save()
