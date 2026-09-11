"""Use an isolated build tree so stale local build output cannot enter wheels."""
from __future__ import annotations

from tempfile import TemporaryDirectory

from setuptools import setup
from setuptools.command.build import build as _build


_BUILD_DIRECTORY = TemporaryDirectory(prefix="hermes-post-design-build-")


class IsolatedBuild(_build):
    def initialize_options(self):
        super().initialize_options()
        self.build_base = _BUILD_DIRECTORY.name


setup(cmdclass={"build": IsolatedBuild})
