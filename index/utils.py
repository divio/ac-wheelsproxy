import re
import functools

from pkg_resources import Requirement


REQ_REGEX = re.compile(r'^(?P<name>[\S]+)(?: \((?P<version>[^\)]+)\))?$')


def parse_requirement(s):
    match = REQ_REGEX.match(s)
    assert match
    return Requirement.parse(''.join(match.groups(default='')))
