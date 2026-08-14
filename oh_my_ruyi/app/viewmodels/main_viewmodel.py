"""ViewModel for the main window."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import QObject, Property, Signal, Slot
from ...core.fsm import (
    PropertyChangedEvent,
    ProvisionStep,
    StateChangedEvent,
    StepChangedEvent,
    WizardStateFSM,
)


class MainViewModel(QObject):
    """Binds WizardStateFSM events to PySide6 Qt Signals/Properties."""

    step_changed = Signal(int)
    property_changed = Signal(str, object)

    def __init__(self, fsm: WizardStateFSM, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.fsm = fsm
        self.fsm.add_observer(self._on_state_changed)

    def _on_state_changed(self, event: StateChangedEvent) -> None:
        if isinstance(event, StepChangedEvent):
            self.step_changed.emit(event.step.value)
        elif isinstance(event, PropertyChangedEvent):
            self.property_changed.emit(event.property_name, event.value)

    @Property(int, notify=step_changed)
    def current_step(self) -> int:
        return self.fsm.step.value

    @Slot(int)
    def set_current_step(self, step_value: int) -> None:
        self.fsm.step = ProvisionStep(step_value)

    @Slot(int)
    def invalidate_from_step(self, step_value: int) -> None:
        self.fsm.invalidate_from(ProvisionStep(step_value))
