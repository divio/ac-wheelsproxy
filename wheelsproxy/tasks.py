import logging

from celery import shared_task


log = logging.getLogger(__name__)


def _build(model, build_id, force):
    try:
        build = model.objects.get(pk=build_id)
    except model.DoesNotExist:
        return

    if not force and build.build:
        # No need to build
        return

    build.rebuild()


@shared_task(ignore_result=True)
def build_internal(build_id, force=False):
    from . import models
    _build(models.Build, build_id, force)


@shared_task(ignore_result=True)
def build_external(build_id, force=False):
    from . import models
    _build(models.ExternalBuild, build_id, force)


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


@shared_task
def compile(requirements_id, force=False):
    from . import models

    requirements_qs = models.CompiledRequirements.objects.all()

    if not force:
        requirements_qs = requirements_qs.filter(
            pip_compilation_status=models.COMPILATION_STATUSES.PENDING,
        )

    try:
        requirements = requirements_qs.get(pk=requirements_id)
    except models.CompiledRequirements.DoesNotExist:
        return

    requirements.recompile()


@shared_task(ignore_result=True)
def populate_platform_environment(platform_id, force=False):
    from . import models
    models.Platform.objects.get(pk=platform_id).populate_environment()

    platform_qs = models.Platform.objects.all()

    if not force:
        platform_qs = platform_qs.filter(
            environment__isnull=True,
        )

    try:
        platform = platform_qs.get(pk=platform_id)
    except models.Platform.DoesNotExist:
        return

    platform.populate_environment()
