import os
import contextlib
from tempfile import mkdtemp
import shutil
import hashlib

from six.moves import urllib, shlex_quote

from docker import Client, tls
from docker.utils import create_host_config

from django.conf import settings
from django.core.files import File


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
            print wheelhouse
            container = self.client.create_container(
                self.image,
                cmd,
                working_dir='/',
                volumes=['/wheelhouse'],
                host_config=create_host_config(binds={
                    wheelhouse: {
                        'bind': '/wheelhouse',
                        'ro': False,
                    }
                }),
            )
            self.client.start(container=container['Id'])
            for s in self.client.attach(container=container['Id'],
                                        stdout=True, stderr=True, stream=True):
                print s
            filename = os.listdir(wheelhouse)[0]
            print filename
            with open(os.path.join(wheelhouse, filename), 'rb') as fh:
                digest = file_digest(hashlib.md5, fh)
                build.build.save(filename, File(fh))

        build.md5_digest = digest
        build.save()
