"""Reactive State Machine and Domain State for provisioning.
This module has zero dependencies on PySide6 and implements an Observer pattern.
"""

from typing import Any, Callable, Dict, List, Optional
from enum import IntEnum

from .models import DeviceChoice, VariantChoice, ComboChoice, PreparedProvision


class ProvisionStep(IntEnum):
    WELCOME = 0
    DEVICE = 1
    VARIANT = 2
    COMBO = 3
    VERSIONS = 4
    PACKAGES = 5
    DOWNLOAD = 6
    STORAGE = 7
    REVIEW = 8
    FLASH = 9
    DONE = 10


class StateChangedEvent:
    """Base event for state changes."""

    pass


class StepChangedEvent(StateChangedEvent):
    def __init__(self, step: ProvisionStep):
        self.step = step


class PropertyChangedEvent(StateChangedEvent):
    def __init__(self, property_name: str, value: Any):
        self.property_name = property_name
        self.value = value


class WizardStateFSM:
    def __init__(self):
        self._observers: List[Callable[[StateChangedEvent], None]] = []

        self._step = ProvisionStep.WELCOME
        self._device: Optional[DeviceChoice] = None
        self._variant: Optional[VariantChoice] = None
        self._combo: Optional[ComboChoice] = None
        self._pkg_atoms: List[str] = []
        self._prepared: Optional[PreparedProvision] = None
        self._host_blkdev_map: Dict[str, Any] = {}
        self._host_blkdev_fingerprints: Dict[str, str] = {}

    def add_observer(self, observer: Callable[[StateChangedEvent], None]):
        self._observers.append(observer)

    def _notify(self, event: StateChangedEvent):
        for observer in self._observers:
            observer(event)

    def _notify_property(self, name: str, value: Any):
        self._notify(PropertyChangedEvent(name, value))

    @property
    def step(self) -> ProvisionStep:
        return self._step

    @step.setter
    def step(self, value: ProvisionStep):
        if self._step != value:
            self._step = value
            self._notify(StepChangedEvent(self._step))

    @property
    def device(self) -> Optional[DeviceChoice]:
        return self._device

    @device.setter
    def device(self, value: Optional[DeviceChoice]):
        self._device = value
        self._notify_property("device", self._device)
        self.variant = None  # cascade invalidation

    @property
    def variant(self) -> Optional[VariantChoice]:
        return self._variant

    @variant.setter
    def variant(self, value: Optional[VariantChoice]):
        self._variant = value
        self._notify_property("variant", self._variant)
        self.combo = None  # cascade invalidation

    @property
    def combo(self) -> Optional[ComboChoice]:
        return self._combo

    @combo.setter
    def combo(self, value: Optional[ComboChoice]):
        self._combo = value
        self._notify_property("combo", self._combo)
        self.pkg_atoms = []
        self.prepared = None
        self.host_blkdev_map = {}
        self.host_blkdev_fingerprints = {}

    @property
    def pkg_atoms(self) -> List[str]:
        return self._pkg_atoms

    @pkg_atoms.setter
    def pkg_atoms(self, value: List[str]):
        self._pkg_atoms = value
        self._notify_property("pkg_atoms", self._pkg_atoms)

    @property
    def prepared(self) -> Optional[PreparedProvision]:
        return self._prepared

    @prepared.setter
    def prepared(self, value: Optional[PreparedProvision]):
        self._prepared = value
        self._notify_property("prepared", self._prepared)

    @property
    def host_blkdev_map(self) -> Dict[str, Any]:
        return self._host_blkdev_map

    @host_blkdev_map.setter
    def host_blkdev_map(self, value: Dict[str, Any]):
        self._host_blkdev_map = value
        self._notify_property("host_blkdev_map", self._host_blkdev_map)

    @property
    def host_blkdev_fingerprints(self) -> Dict[str, str]:
        return self._host_blkdev_fingerprints

    @host_blkdev_fingerprints.setter
    def host_blkdev_fingerprints(self, value: Dict[str, str]):
        self._host_blkdev_fingerprints = value
        self._notify_property(
            "host_blkdev_fingerprints", self._host_blkdev_fingerprints
        )
