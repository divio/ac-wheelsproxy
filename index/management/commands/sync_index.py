import itertools

import six
from six.moves import zip as iterzip

import djclick as click

from django.utils.text import slugify

from ... import models, tasks, utils


@click.command()
@click.option('--initial/--no-initial',
              help='Perform the initial sync (not using diffs).')
@click.argument('index')
def command(initial, index):
    index = models.BackingIndex.objects.get(slug=index)
    last_serial = index.last_update_serial

    if not last_serial or initial:
        chunk_size = 100  # Number of packages to update per task
        concurrency = 20  # Number of concurrent tasks

        # As we are syncing everything, get the current serial.
        last_serial = index.client.changelog_last_serial()

        # Get the set of all existing packages. We will discard IDs of updated
        # packages from it and then remove all the remaining packages.
        all_package_ids = set(index.package_set.values_list('id', flat=True))

        # Get all the names of the packages on the selected index.
        click.secho('Fetching list of packges from {}...'.format(index.url),
                    fg='yellow')
        all_packages = index.client.list_packages()

        # Import all packages metadata in different chunks and tasks.
        click.secho('Importing {} packages...'.format(len(all_packages)),
                    fg='yellow')
        args = iterzip(
            itertools.repeat(index.pk),
            utils.iter_chunks((slugify(p) for p in all_packages), chunk_size),
        )
        results_iterator = utils.bounded_submitter(
            tasks.import_packages,
            concurrency,
            args,
        )
        with click.progressbar(length=len(all_packages), show_pos=True) as bar:
            for succeded, ignored, failed in results_iterator:
                bar.update(len(succeded) + len(ignored) + len(failed))
                all_package_ids -= set(succeded.values())
                if failed:
                    click.echo('')
                    for k, v in six.iteritems(failed):
                        click.secho('Failed to import {} ({})'.format(k, v),
                                    fg='red')

        # Remove the set of not-updated (i.e. not found on the index anymore)
        # packages from the database.
        click.secho('Removing {} outdated packages...'
                    .format(len(all_package_ids)), fg='yellow')
        index.package_set.filter(pk__in=all_package_ids).delete()

    # Sync everything since the last serial, also when initial == True, as
    # something might have changed in the meantime...
    for event in index.client.changelog_since_serial(last_serial):
        # TODO: Take action
        # package_name, _, _, action, last_serial = event
        print event

    index.last_update_serial = last_serial
    index.save()
