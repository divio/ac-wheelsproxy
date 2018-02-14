import re

import furl

from pkg_resources import Requirement, yield_lines, safe_version


REQ_REGEXES = [
    # name (specs,...)
    re.compile(r'^(?P<name>[\S]+)(?: \((?P<version>[^\)]+)\))?$'),
    # name op single spec
    re.compile(r'^(?P<name>[\S]+) (?P<spec>[\S]+) (?P<version>[\S]+)$'),
]


def parse_requirement(s):
    for regex in REQ_REGEXES:
        match = regex.match(s)
        if match:
            break
    else:
        raise ValueError('Invalid dependency specifier')
    return Requirement.parse(''.join(match.groups(default='')))


def normalize_package_name(package_name):
    return re.sub(r'(\.|-|_)+', '-', package_name.lower())


def normalize_version(version):
    return safe_version(version)


class UniquesIterator(object):
    def __init__(self, key=None):
        self.seen = set()
        self.key = key or (lambda obj: obj)

    def not_seen_yet(self, objects):
        for obj in objects:
            k = self.key(obj)
            if k not in self.seen:
                self.seen.add(k)
                yield obj

    __call__ = not_seen_yet


def split_requirements(strs):
    """Yield ``Requirement`` objects for each specification in `strs`
    `strs` must be a string, or a (possibly-nested) iterable thereof.
    """
    # create a steppable iterator, so we can handle \-continuations
    lines = iter(yield_lines(strs))

    for line in lines:
        # Drop comments -- a hash without a space may be in a URL.
        if ' #' in line:
            line = line[:line.find(' #')]
        # If there is a line continuation, drop it, and append the next line.
        if line.endswith('\\'):
            line = line[:-2].strip()
            line += next(lines)
        yield line.strip()


def parse_requirements(strs):
    for req in split_requirements(strs):
        try:
            url = furl.furl(req)
        except Exception:
            pass
        else:
            if url.scheme:
                req = url.fragment.args['egg'].split('==')[0]
                yield Requirement('{}@{}'.format(req, url))
                continue

        yield Requirement(req)


def retry_call(times, func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except Exception:
            if times:
                times -= 1
            else:
                raise
