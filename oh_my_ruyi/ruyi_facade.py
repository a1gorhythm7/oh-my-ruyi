"""Backward-compatibility module for ruyi provisioning facade."""

import sys
from .infra import ruyi_adapter
from .infra.ruyi_adapter import *  # noqa: F403
from .infra.os_storage import (
    BlockDeviceChoice as BlockDeviceChoice,
    is_disk_or_child_mounted as is_disk_or_child_mounted,
    is_path_mounted_blkdev as is_path_mounted_blkdev,
    list_disks as list_disks,
    storage_platform_hint as storage_platform_hint,
)


class _FacadeModule(sys.modules[__name__].__class__):
    def __getattr__(self, name: str) -> object:
        if name in ("__dict__",):
            return object.__getattribute__(self, name)
        return getattr(ruyi_adapter, name)

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        setattr(ruyi_adapter, name, value)


sys.modules[__name__].__class__ = _FacadeModule
