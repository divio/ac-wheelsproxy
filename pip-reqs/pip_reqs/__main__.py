import click

from .client import WheelsproxyClient
from .parser import RequirementsParser


@click.group()
@click.option('--wheelsproxy', '-w', envvar='WHEELSPROXY_URL', required=True)
@click.pass_context
def main(ctx, wheelsproxy):
    ctx.obj = WheelsproxyClient(wheelsproxy)


@main.command()
@click.pass_obj
@click.argument('infile', default='requirements.in', required=False,
                type=click.Path(exists=True))
@click.argument('outfile', default='requirements.txt', required=False,
                type=click.File('wb', lazy=True))
def compile(obj, infile, outfile):
    parser = RequirementsParser()
    ext_reqs, local_reqs = parser.parse(infile)
    compiled_reqs = obj.compile('\n'.join(ext_reqs))
    outfile.write(compiled_reqs)
    outfile.write('\n'.join([
        '',
        '# The following packages are available only locally.',
        '# Their dependencies *have* been considered while',
        '# resolving the full dependency tree:',
    ] + local_reqs))
    outfile.write('\n')


@main.command()
@click.pass_obj
@click.argument('infile', default='requirements.txt', required=False,
                type=click.File('rb'))
@click.argument('outfile', default='requirements.urls', required=False,
                type=click.File('wb', lazy=True))
def resolve(obj, infile, outfile):
    outfile.write(obj.resolve(infile.read()))


if __name__ == '__main__':
    main()
