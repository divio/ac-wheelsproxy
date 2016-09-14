from functools import partial

import attr

from pkg_resources import parse_version, Requirement

from django.core.exceptions import ObjectDoesNotExist

from wheelsproxy import depgraph, utils


@attr.s
class Distribution(object):
    name = attr.ib()
    releases = attr.ib(init=False, default=attr.Factory(list))

    def add_release(self, rel):
        self.releases.append(rel)

    def get_versions(self):
        return sorted([
            (rel.version, rel) for rel in self.releases
        ], reverse=True)


@attr.s
class Release(object):
    distribution = attr.ib()
    version = attr.ib(convert=parse_version)
    requirements = attr.ib(convert=partial(map, Requirement), default=[])

    def get_build(self, platform):
        return Build(self, platform)

    @property
    def package(self):
        return Distribution(self.distribution)

    @property
    def parsed_version(self):
        return self.version

    @property
    def requirement(self):
        return Requirement('{}=={}'.format(self.distribution, self.version))


@attr.s
class Build(object):
    release = attr.ib()
    platform = attr.ib()

    def is_built(self):
        return True

    def is_external(self):
        return False

    def iter_requirements(self, extras=None):
        return iter(self.release.requirements)


class Index(object):
    def __init__(self, releases):
        self.distributions = {}
        for rel in releases:
            distribution = self.get_package(rel.distribution)
            distribution.add_release(rel)

    def get_package(self, package_name, create=True):
        normalized_package_name = utils.normalize_package_name(package_name)
        try:
            return self.distributions[normalized_package_name]
        except KeyError:
            if create:
                self.distributions[normalized_package_name] = (
                    Distribution(normalized_package_name))
                return self.distributions[normalized_package_name]
            else:
                raise ObjectDoesNotExist('Distribution not found')


class Platform(object):
    pass


def simple_compile(distributions, requirements):
    graph = depgraph.DependencyGraph(
        [Index(distributions)],
        Platform(),
    )
    graph.compile(requirements)
    return graph


# def test_no_reqs():
#     graph = simple_compile([], [])
#
#     assert not graph
#
#     graph = simple_compile([
#         Release('dist-a', '1.0'),
#     ], [])
#
#     assert not graph
#
#
# def test_single_req():
#     graph = simple_compile([
#         Release('dist-a', '1.0'),
#     ], [
#         'dist-a',
#     ])
#
#     assert len(graph) == 1
#     assert 'dist-a==1.0' in graph
#
#
# def test_markers():
#     pass
#
#
# def test_deps_environment():
#     pass
#
#
# def test_remove_unused():
#     pass
#
#
# def test_multi_index():
#     pass


def test_compile():
    graph = simple_compile([
        Release('dist-a', '1.0', ['dist-c']),
        Release('dist-b', '2.0', ['dist-e']),
        Release('dist-c', '3.0', ['dist-d']),
        Release('dist-c', '1.0'),
        Release('dist-d', '1.0'),
        Release('dist-e', '1.0', ['dist-c<=2.0']),
    ], [
        'dist-a',
        'dist-b',
    ])

    assert 'dist-a' in graph
    assert 'dist-b==2.0' in graph
    assert 'dist-c' in graph
    assert 'dist-c<2.0' in graph
    assert 'dist-c==3.0' not in graph
    assert 'dist-d' not in graph
