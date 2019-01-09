import argparse
import os
import sys

from .client import WheelsproxyClient, CompilationError
from .parser import RequirementsParser


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w", "--wheelsproxy", default=os.environ.get("WHEELSPROXY_URL")
    )
    subparsers = parser.add_subparsers()

    compile_parser = subparsers.add_parser("compile")
    compile_parser.set_defaults(func=compile)
    compile_parser.add_argument("infile", default="requirements.in")
    compile_parser.add_argument("outfile", default="requirements.txt")

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.set_defaults(func=resolve)
    resolve_parser.add_argument("infile", default="requirements.txt")
    resolve_parser.add_argument("outfile", default="requirements.urls")

    args = parser.parse_args()

    if not args.wheelsproxy:
        print(
            (
                "Either the --wheelsproxy argument or a WHEELSPROXY_URL "
                "environment variable are required."
            ),
            file=sys.stderr,
        )

    client = WheelsproxyClient(args.wheelsproxy)
    args.func(client, args)


def compile(client, args):
    parser = RequirementsParser()
    ext_reqs, local_reqs = parser.parse(args.infile)
    try:
        compiled_reqs = client.compile(b"\n".join(ext_reqs))
    except CompilationError as e:
        print(e.args[0], file=sys.stderr)
        sys.exit(1)
    with open(args.outfile, "wb") as fh:
        fh.write(compiled_reqs)
        if local_reqs:
            fh.write(
                b"\n".join(
                    [
                        b"",
                        b"# The following packages are available only locally.",
                        b"# Their dependencies *have* been considered while",
                        b"# resolving the full dependency tree:",
                    ]
                    + local_reqs
                )
            )
        fh.write(b"\n")


def resolve(client, args):
    with open(args.infile, "rb") as fh:
        urls = client.resolve(fh.read())

    with open(args.outfile, "wb") as fh:
        fh.write(urls)


if __name__ == "__main__":
    main()
