import itertools
import collections

import six
from six.moves import zip as iterzip

import djclick as click

from ... import models, tasks


def bounded_submitter(task, size, args_iter):
    results = collections.deque()

    for i in range(size):
        try:
            args = next(args_iter)
        except StopIteration:
            break
        else:
            results.append(task.delay(*args))

    while results:
        res = results.popleft().get()
        try:
            args = next(args_iter)
        except StopIteration:
            break
        else:
            results.append(task.delay(*args))
        yield res

    while results:
        res = results.popleft().get()
        yield res


def iter_chunks(iterable, size):
    iterable = iter(iterable)
    while True:
        res = []
        for i in range(size):
            try:
                res.append(next(iterable))
            except StopIteration:
                break
        if not res:
            break
        yield res


@click.command()
@click.option('--initial/--no-initial',
              help='Perform the initial sync (not using diffs).')
@click.argument('index')
def command(initial, index):
    index = models.BackingIndex.objects.get(slug=index)
    last_serial = index.last_update_serial

    if not last_serial or initial:
        chunk_size = 150  # Number of packages to update per task
        concurrency = 30  # Number of concurrent tasks

        # As we are syncing everything, get the current serial
        last_serial = index.client.changelog_last_serial()

        all_package_ids = set(index.package_set.values_list('id', flat=True))

        click.secho('Fetching list of packges from {}...'.format(index.url),
                    fg='yellow')
        all_packages = index.client.list_packages()

        click.secho('Importing {} packages...'.format(len(all_packages)),
                    fg='yellow')
        args = iterzip(
            itertools.repeat(index.pk),
            iter_chunks(all_packages, chunk_size),
        )
        results_iterator = bounded_submitter(
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

        click.secho('Removing {} outdated packages...'
                    .format(len(all_package_ids)), fg='yellow')
        index.package_set.exclude(pk__in=all_package_ids).delete()

    # Sync everything since the last serial, also when initial == True, as
    # something might have changed in the meantime...
    print index.client.changelog_since_serial(last_serial)

    index.last_update_serial = last_serial
    index.save()
