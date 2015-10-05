import logging

import six

import requests

from celery import shared_task


log = logging.getLogger(__name__)


@shared_task
def build(build_id, force=False):
    from . import models

    try:
        build = models.Build.objects.get(pk=build_id)
    except models.Build.DoesNotExist:
        pass

    if not force and build.build:
        # No need to build
        return

    build.rebuild()


def import_package(index, package_name, session=None):
    from . import models
    try:
        payload = index.get_package_details(package_name, session=session)
    except models.PackageNotFound:
        return
    versions = payload['releases']
    if not versions:
        return
    package = index.get_package(package_name)
    release_ids = []
    for version, releases in six.iteritems(versions):
        release_details = package.get_best_release(releases)
        if not release_details:
            continue
        release = package.get_release(version, release_details)
        release_ids.append(release.pk)
    if release_ids:
        # Remove outdated releases
        package.release_set.exclude(pk__in=release_ids).delete()
    package.expire_cache()
    return package.pk if release_ids else None


@shared_task
def import_packages(index_id, package_names):
    from . import models
    session = requests.Session()
    index = models.BackingIndex.objects.get(pk=index_id)
    succeded = {}
    failed = {}
    ignored = []
    for package_name in package_names:
        try:
            id = import_package(index, package_name, session)
        except Exception as e:
            log.exception('Failed to import {} from {}'.format(
                package_name, index.url))
            failed[package_name] = '{}.{}: {}'.format(
                e.__class__.__module__, e.__class__.__name__, str(e))
        else:
            if id:
                succeded[package_name] = id
            else:
                ignored.append(package_name)
    return succeded, ignored, failed
