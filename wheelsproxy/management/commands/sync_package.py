import djclick as click
from djclick.params import ModelInstance

from ...models import BackingIndex


@click.command()
@click.argument('index', type=ModelInstance(BackingIndex, lookup='slug'))
@click.argument('package', type=ModelInstance(Package, lookup='slug'))
def command(index, package):
    index.import_package(package.slug)

