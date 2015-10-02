from celery import shared_task


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
