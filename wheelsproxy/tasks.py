import logging

from celery import shared_task


log = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def build(build_id, force=False):
    from . import models

    try:
        build = models.Build.objects.get(pk=build_id)
    except models.Build.DoesNotExist:
        return

    if not force and build.build:
        # No need to build
        return

    build.rebuild()


@shared_task
def import_packages(index_id, package_names):
    from . import models
    index = models.BackingIndex.objects.get(pk=index_id)
    succeded, failed, ignored = {}, {}, []
    for package_name in package_names:
        try:
            id = index.import_package(package_name)
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


@shared_task(ignore_result=True)
def sync_index(index_id):
    from . import models
    index = models.BackingIndex.objects.get(pk=index_id)
    if not index.last_update_serial:
        log.warning('Skipping index without intial sync "{}"'
                    .format(index.slug))
        return
    log.info('Syncing index "{}"'.format(index.slug))
    index.sync()


@shared_task(ignore_result=True)
def sync_indexes():
    from . import models
    for index_pk in models.BackingIndex.objects.values_list('pk', flat=True):
        sync_index(index_pk)
