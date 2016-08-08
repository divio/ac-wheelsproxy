import collections


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
