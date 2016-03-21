import re
import collections

from pkg_resources import Requirement


REQ_REGEX = re.compile(r'^(?P<name>[\S]+)(?: \((?P<version>[^\)]+)\))?$')


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
        finally:
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


def parse_requirement(s):
    match = REQ_REGEX.match(s)
    assert match
    return Requirement.parse(''.join(match.groups(default='')))
