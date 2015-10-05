import logging

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


@shared_task
def import_packages(index_id, package_names):
    from . import models
    session = requests.Session()
    index = models.BackingIndex.objects.get(pk=index_id)
    succeded, failed, ignored = {}, {}, []
    for package_name in package_names:
        try:
            id = index.import_package(package_name, session)
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
