import re

from pkg_resources import Requirement


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
