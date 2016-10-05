import os
import json
import zipfile
import contextlib
from tempfile import mkdtemp
import shutil
import hashlib
import io

from six.moves import shlex_quote

import furl

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


def get_docker_client(dsn):
    tls_config = None
    url = furl.furl(dsn)
    cert_path = url.args.get('cert_path')
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
    else:
        host = dsn
    return Client(host, tls=tls_config, version='auto')


def file_digest(algorithm, fh, chunk_size=4096):
    hash = algorithm()
    for chunk in iter(lambda: fh.read(chunk_size), b''):
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


def extract_wheel_meta(fh):
    with zipfile.ZipFile(fh) as z:
        for member in z.infolist():
            try:
                dirname, basename = member.filename.split('/')
            except ValueError:
                continue
            if dirname.endswith('.dist-info') and basename == 'metadata.json':
                return json.loads(z.read(member.filename).decode('utf-8'))
        else:
            return None


class DockerBuilder(object):
    def __init__(self, platform_spec):
        self.image = platform_spec['image']
        self.client = get_docker_client(settings.BUILDS_DOCKER_DSN)

    def get_environment(self):
        log = io.StringIO()
        env = io.StringIO()

        pycmd = '; '.join([
            'import sys, json',
            'from pkg_resources.extern.packaging.markers import default_environment',  # NOQA
            'json.dump(default_environment(), sys.stdout)',
        ])

        cmd = ' '.join([
            'python',
            '-c',
            shlex_quote(pycmd),
        ])

        image, tag = split_image_name(self.image)
        consume_output(self.client.pull(image, tag, stream=True), log)

        container = self.client.create_container(self.image, cmd)
        self.client.start(container=container['Id'])

        consume_output(
            self.client.attach(container=container['Id'],
                               stdout=True, stderr=True, stream=True),
            env,
        )

        self.client.remove_container(container=container['Id'], v=True)

        return json.loads(env.getvalue())

    def build(self, build):
        build_command = ' '.join([
            'pip', 'wheel',
            '--no-deps',
            '--no-clean',
            '--no-index',
            '--wheel-dir', '/wheelhouse',
            shlex_quote(build.original_url),
        ])
        setup_commands = [
            line.strip()
            for line in build.setup_commands.splitlines()
            if line.strip()
        ]
        commands = ' && '.join(setup_commands + [build_command])
        cmd = 'sh -c {}'.format(shlex_quote(commands))

        build_log = io.StringIO()
        build_log.write(cmd)
        build_log.write('\n')

        with tempdir(dir=settings.TEMP_BUILD_ROOT) as wheelhouse:
            image, tag = split_image_name(self.image)
            consume_output(
                # TODO: Add support for custom registries and auth_config
                self.client.pull(image, tag, stream=True),
                build_log,
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
                    },
                }),
            )

            build_start = timezone.now()
            self.client.start(container=container['Id'])
            consume_output(
                self.client.attach(container=container['Id'],
                                   stdout=True, stderr=True, stream=True),
                build_log,
            )
            build_end = timezone.now()

            self.client.remove_container(container=container['Id'], v=True)

            build.build_log = build_log.getvalue()
            build.build_duration = (build_end - build_start).total_seconds()
            build.build_timestamp = timezone.now()
            build.save()

            filenames = os.listdir(wheelhouse)

            if filenames:
                assert len(filenames) == 1
                filename = filenames[0]

                with open(os.path.join(wheelhouse, filename), 'rb') as fh:
                    build.metadata = extract_wheel_meta(fh)
                    fh.seek(0)
                    build.md5_digest = file_digest(hashlib.md5, fh)
                    fh.seek(0)
                    build.build.save(filename, File(fh))
                    fh.seek(0)
                    build.filesize = build.build.size
                    build.save()
            else:
                raise RuntimeError('Build failed')

    def compile(self, reqs):
        from .models import COMPILATION_STATUSES

        cmd = ' '.join([
            'pip-compile',
            '--verbose',
            '--no-index',
            '--index-url', reqs.index_url,
            '/workspace/requirements.in',
        ])

        compilation_log = io.StringIO()
        compilation_start = timezone.now()

        with tempdir(dir=settings.TEMP_BUILD_ROOT) as workspace:
            with open(os.path.join(workspace, 'requirements.in'), 'w') as fh:
                fh.write(reqs.requirements)

            image, tag = split_image_name(self.image)
            consume_output(
                self.client.pull(image, tag, stream=True),
                compilation_log,
            )

            cache_dir = os.path.join(
                settings.COMPILE_CACHE_ROOT,
                reqs.platform.slug,
            )
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            container = self.client.create_container(
                self.image,
                cmd,
                working_dir='/',
                volumes=[
                    '/wheelhouse',
                    '/root/.cache',
                ],
                host_config=self.client.create_host_config(binds={
                    workspace: {
                        'bind': '/workspace',
                        'ro': False,
                    },
                    cache_dir: {
                        'bind': '/root/.cache',
                        'ro': False,
                    },
                }),
            )

            self.client.start(container=container['Id'])
            consume_output(
                self.client.attach(container=container['Id'],
                                   stdout=True, stderr=True, stream=True),
                compilation_log,
            )

            self.client.remove_container(container=container['Id'], v=True)

            reqs.pip_compilation_log = compilation_log.getvalue()
            compilation_end = timezone.now()
            reqs.pip_compilation_duration = (
                compilation_end - compilation_start
            ).total_seconds()
            reqs.pip_compilation_timestamp = timezone.now()
            reqs.save(update_fields=[
                'pip_compilation_log',
                'pip_compilation_duration',
                'pip_compilation_timestamp',
            ])

            compiled_requirements = os.path.join(workspace, 'requirements.txt')

            if os.path.exists(compiled_requirements):
                with open(compiled_requirements, 'r') as fh:
                    reqs.pip_compiled_requirements = fh.read()
                    reqs.pip_compilation_status = COMPILATION_STATUSES.DONE
                    reqs.save(update_fields=[
                        'pip_compiled_requirements',
                        'pip_compilation_status',
                    ])
            else:
                reqs.pip_compiled_requirements = ''
                reqs.pip_compilation_status = COMPILATION_STATUSES.FAILED
                reqs.save(update_fields=[
                    'pip_compiled_requirements',
                    'pip_compilation_status',
                ])
                raise RuntimeError('Compilation failed')
