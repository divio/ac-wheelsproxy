#!/usr/bin/env python

import ast
import re
import os
import sys

from setuptools import setup, find_packages


NAME = "pip-reqs"
PACKAGE = "pip_reqs"


if sys.argv[-1] == "publish":
    os.system("python setup.py sdist bdist_wheel upload")
    sys.exit()


class Setup:
    @staticmethod
    def read(fname, fail_silently=False):
        """
        Read the content of the given file. The path is evaluated from the
        directory containing this file.
        """
        try:
            filepath = os.path.join(os.path.dirname(__file__), fname)
            with open(filepath, "rt", encoding="utf8") as f:
                return f.read()
        except Exception:
            if not fail_silently:
                raise
            return ""

    @staticmethod
    def metavar(name):
        data = Setup.read(os.path.join(PACKAGE, "__init__.py"))
        value = (
            re.search(u"__{}__\s*=\s*u?'([^']+)'".format(name), data)
            .group(1)
            .strip()
        )
        return value

    @staticmethod
    def longdesc():
        return Setup.read("README.rst") + "\n\n" + Setup.read("CHANGELOG.rst")

    @staticmethod
    def shortdesc():
        node = ast.parse(Setup.read(os.path.join(PACKAGE, "__init__.py")))
        docstring = ast.get_docstring(node)
        return docstring.split("\n\n")[0].strip().replace("\n", " ")


setup(
    name=NAME,
    version=Setup.metavar("version"),
    author=Setup.metavar("author"),
    author_email=Setup.metavar("email"),
    zip_safe=False,
    url=Setup.metavar("url"),
    license=Setup.metavar("license"),
    packages=find_packages(),
    package_dir={PACKAGE: PACKAGE},
    description=Setup.shortdesc(),
    long_description=Setup.longdesc(),
    entry_points=Setup.read("entry-points.ini", True),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
