import re

from pkg_resources import Requirement
from pkg_resources import yield_lines


REQ_REGEX = re.compile(r'^(?P<name>[\S]+)(?: \((?P<version>[^\)]+)\))?$')


def parse_requirement(s):
    match = REQ_REGEX.match(s)
    assert match
    return Requirement.parse(''.join(match.groups(default='')))


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
        yield Requirement(req)
