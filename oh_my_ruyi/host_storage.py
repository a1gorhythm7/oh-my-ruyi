"""Backward-compatibility module for host storage discovery and validation."""

import sys
from .infra import os_storage
from .infra.os_storage import *  # noqa: F403

_target_module = os_storage


class _HostStorageModule(sys.modules[__name__].__class__):
    def __getattr__(self, name: str) -> object:
        if name in ("_target_module", "__dict__"):
            return object.__getattribute__(self, name)
        return getattr(os_storage, name)

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        setattr(os_storage, name, value)


sys.modules[__name__].__class__ = _HostStorageModule
