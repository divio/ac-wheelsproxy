import logging
from collections import namedtuple
import io

import six

import requests

import furl

from six.moves import xmlrpc_client, range

from execnet.gateway_base import Unserializer

from .utils import retry_call


log = logging.getLogger(__name__)


class PackageNotFound(Exception):
    pass


class Release(namedtuple('Release', ['url', 'md5_digest', 'type'])):
    @staticmethod
    def guess_type(url):
        if url.endswith('.tar.bz2'):
            return 'sdist'
        if url.endswith('.whl'):
            return 'bdist_wheel'
        if url.endswith('.zip'):
            return 'sdist'
        if url.endswith('.tar.gz'):
            return 'sdist'
        if url.endswith('.tgz'):
            return 'sdist'

        if url.endswith('.egg'):
            return None
        if url.endswith('.rpm'):
            return None
        if url.endswith('.exe'):
            return None
        if url.endswith('.msi'):
            return None
        if url.endswith('.dmg'):
            return None

        raise ValueError('Cannot guess package type of `{}`'.format(url))


class IndexAPIClient(object):
    def __init__(self, url):
        self.url = url

    def changelog_last_serial(self):
        raise NotImplementedError

    def list_packages(self):
        raise NotImplementedError

    def iter_updated_packages(self, since_serial):
        raise NotImplementedError

    def get_package_releases(self, package_name):
        raise NotImplementedError

    def get_version_releases(self, package_name, version):
        raise NotImplementedError


class PyPIClient(IndexAPIClient):
    def __init__(self, model):
        super(PyPIClient, self).__init__(model)
        self.client = xmlrpc_client.ServerProxy(self.url)
        self.session = requests.Session()

    def changelog_last_serial(self):
        return self.client.changelog_last_serial()

    def list_packages(self):
        return self.client.list_packages()

    def iter_updated_packages(self, since_serial):
        events = self.client.changelog_since_serial(since_serial)
        while events:
            seen_packages = set()
            for event in events:
                package_name, _, _, _, event_serial = event
                if package_name in seen_packages:
                    # This package was already seen once during this
                    # loop, which means we have already updated it once.
                    yield None, event_serial
                else:
                    seen_packages.add(package_name)
                    yield package_name, event_serial
            events = self.client.changelog_since_serial(event_serial)

    def _clean_releases(self, version_details):
        return [Release(
            rel['url'],
            rel['md5_digest'],
            rel['packagetype'],
        ) for rel in version_details]

    def get_package_releases(self, package_name):
        url = furl.furl(self.url)
        url.path.add([package_name, 'json'])

        response = self.session.get(url)
        if response.status_code == 404:
            raise PackageNotFound()
        if response.status_code >= 300:
            content = response.content
            log.warning('Invalid response {} from index {} with content: {!r}'
                        .format(response.status_code, self.url, content))
            raise RuntimeError('Invalid response from index: {}'
                               .format(response.status_code))

        releases = response.json()['releases']
        return {k: self._clean_releases(v) for k, v in six.iteritems(releases)}


class DevPIClient(IndexAPIClient):
    def __init__(self, model):
        super(DevPIClient, self).__init__(model)
        self.api_session = requests.Session()
        self.api_session.headers.update({
            'Accept': 'application/json',
        })

    def changelog_last_serial(self):
        r = self.api_session.get(self.url)
        return int(r.headers['x-devpi-serial']) - 1

    def master_uuid(self):
        r = self.api_session.get(self.url)
        return r.headers.get('x-devpi-master-uuid')

    def _iter_stage_packages(self, stage_url):
        r = self.api_session.get(stage_url)
        r.raise_for_status()
        payload = r.json()

        root_url = furl.furl(stage_url)
        root_url.path.set(root_url.path.segments[:-2])

        if payload['result']['type'] == 'mirror':
            return

        for base in payload['result']['bases']:
            url = root_url.copy()
            url.path.add(base.split('/'))
            for project in self._iter_stage_packages(url):
                yield project

        for project in payload['result']['projects']:
            yield project

    def list_packages(self):
        return list(set(self._iter_stage_packages(self.url)))

    def _clean_releases(self, version_details):
        releases = (
            (rel, Release.guess_type(rel['href']))
            for rel in version_details.get('+links', [])
        )

        return [Release(
            rel['href'],
            # TODO: Add support for hashspec and alternative hashes
            #       (newer devpi versions support sha256)
            rel.get('md5', ''),
            type,
        ) for rel, type in releases if type]

    def get_package_releases(self, package_name):
        url = furl.furl(self.url)
        url.path.add(package_name)

        response = self.api_session.get(url)
        if response.status_code == 404:
            raise PackageNotFound()
        if response.status_code >= 300:
            content = response.content
            log.warning('Invalid response {} from index {} with content: {!r}'
                        .format(response.status_code, url, content))
            raise RuntimeError('Invalid response from index: {}'
                               .format(response.status_code))

        releases = response.json()['result']
        return {k: self._clean_releases(v) for k, v in six.iteritems(releases)}

    def _load_payload(self, payload):
        payload = io.BytesIO(payload)
        return (
            Unserializer(payload, strconfig=(False, False))
            .load(versioned=False)
        )

    def iter_updated_packages(self, since_serial):
        changelog_url = furl.furl(self.url)
        changelog_url.path.set(changelog_url.path.segments[:-2])
        changelog_url.path.add('+changelog')

        current_serial = self.changelog_last_serial()
        master_uuid = self.master_uuid()

        headers = {}
        if master_uuid:
            headers['x-devpi-expected-master-id'] = master_uuid

        while since_serial < current_serial:
            seen_packages = set()
            for event_serial in range(since_serial + 1, current_serial + 1):
                url = changelog_url.copy()
                url.path.add(str(event_serial))
                response = retry_call(3, self.api_session.get,
                                      url, timeout=15, headers=headers)
                response.raise_for_status()

                event = self._load_payload(response.content)[0]
                for k, v in event.items():
                    event_type, backserial, value = v
                    method_name = 'handle_{}'.format(event_type.upper())
                    package_name = getattr(self, method_name)(k, value)
                    if not package_name or package_name in seen_packages:
                        # The event did not contain any relevant information
                        # or this package was already seen once during this
                        # loop, which means we have already updated it once.
                        yield None, event_serial
                    else:
                        seen_packages.add(package_name)
                        yield package_name, event_serial
            since_serial = current_serial
            current_serial = self.changelog_last_serial()

    def handle_USERLIST(self, key, payload):
        pass  # Nothing to do here

    def handle_USER(self, key, payload):
        pass  # Nothing to do here

    def handle_PROJNAMES(self, key, payload):
        pass  # Nothing to do here

    def handle_PROJVERSION(self, key, payload):
        return key.split('/')[2]

    def handle_PROJVERSIONS(self, key, payload):
        return key.split('/')[2]

    def handle_STAGEFILE(self, key, payload):
        if payload:
            # A new file was added
            return payload.get('projectname')

    def handle_PYPIFILE_NOMD5(self, key, payload):
        pass  # Nothing to do here

    def handle_PYPILINKS(self, key, payload):
        pass  # Nothing to do here

    def handle_PROJSIMPLELINKS(self, key, payload):
        return key.split('/')[2]
