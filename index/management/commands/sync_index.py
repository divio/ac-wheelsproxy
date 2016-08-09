import itertools

import six
from six.moves import zip as iterzip

import djclick as click
from djclick.params import ModelInstance

from celery_app import utils

from ...models import BackingIndex
from ...tasks import import_packages


@click.command()
@click.option('--initial/--no-initial',
              help='Perform the initial sync (not using diffs).')
@click.argument('index', type=ModelInstance(BackingIndex, lookup='slug'))
def command(initial, index):
    if not index.last_update_serial or initial:
        chunk_size = 150  # Number of packages to update per task
        concurrency = 30  # Number of concurrent tasks

        # As we are syncing everything, get the current serial.
        index.last_update_serial = index.client.changelog_last_serial()

        # Get the set of all existing packages. We will discard IDs of updated
        # packages from it and then remove all the remaining packages.
        all_package_ids = set(index.package_set.values_list('id', flat=True))

        # Get all the names of the packages on the selected index.
        click.secho('Fetching list of packages from {}...'.format(index.url),
                    fg='yellow')
        all_packages = index.client.list_packages()

        # Import all packages metadata in different chunks and tasks.
        click.secho('Importing {} packages...'.format(len(all_packages)),
                    fg='yellow')
        # Create a generator of (index.pk, all_packages[i:i+chunk_size]) tuples
        args = iterzip(
            itertools.repeat(index.pk),
            utils.iter_chunks(all_packages, chunk_size),
        )
        # Submit each tuple in args to the workers, but limit it to at most
        # `concurrency` running tasks
        results_iterator = utils.bounded_submitter(
            import_packages,
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
        index.save(update_fields=['last_update_serial'])

    # Sync everything since the last serial, also when initial == True, as
    # something might have changed in the meantime...
    events = index.client.changelog_last_serial() - index.last_update_serial
    if events:
        click.secho('Syncing remaining updates...', fg='yellow')
        sync_iter = index.itersync()
        with click.progressbar(sync_iter, length=events, show_pos=True) as bar:
            for event in bar:
                pass
