import djclick as click
from djclick.params import ModelInstance

from ...models import BackingIndex, Platform
from ...depgraph import DependencyGraph, GraphFormatter


@click.command()
@click.argument('index', nargs=-1,
                type=ModelInstance(BackingIndex, lookup='slug'))
@click.argument('platform', type=ModelInstance(Platform, lookup='slug'))
@click.argument('requirements_in', type=click.File('r'))
@click.argument('requirements_txt', type=click.File('w'))
def command(index, platform, requirements_in, requirements_txt):
    graph = DependencyGraph(index, platform)
    graph.compile(requirements_in.read())

    formatter = GraphFormatter()
    formatter.write(requirements_txt, graph)
