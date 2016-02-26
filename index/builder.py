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


def consume_output(stream, fh, encoding='utf-8'):
    for chunk in stream:
        fh.write(chunk.decode(encoding))


def split_image_name(name):
    image_tag = name.rsplit(':', 1)
    if len(image_tag) == 2:
        image, tag = image_tag
    else:
        image, tag = image_tag[0], None
    return image, tag


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

        build_log_io = io.StringIO()
        build_log = ''

        with tempdir(dir=settings.TEMP_BUILD_ROOT) as wheelhouse:
            image, tag = split_image_name(self.image)
            consume_output(
                # TODO: Add support for custom/insecure registries and
                # auth_config
                self.client.pull(image, tag, stream=True),
                build_log_io,
            )

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
            consume_output(
                self.client.attach(container=container['Id'],
                                   stdout=True, stderr=True, stream=True),
                build_log_io,
            )
            build_log = build_log_io.getvalue()
            build_duration = timezone.now() - build_start

            filenames = os.listdir(wheelhouse)
            assert len(filenames) == 1
            filename = filenames[0]
            with open(os.path.join(wheelhouse, filename), 'rb') as fh:
                digest = file_digest(hashlib.md5, fh)
                build.build.save(filename, File(fh))

        build.build_duration = build_duration.seconds
        build.build_log = build_log
        build.build_timestamp = timezone.now()
        build.md5_digest = digest
        build.filesize = build.build.size
        build.save()
