from __future__ import annotations

from oh_my_ruyi.core.fsm import (
    PropertyChangedEvent,
    ProvisionStep,
    StateChangedEvent,
    StepChangedEvent,
    WizardStateFSM,
)
from oh_my_ruyi.core.models import (
    ComboChoice,
    DeviceChoice,
    PreparedProvision,
    VariantChoice,
)


def test_fsm_initial_state() -> None:
    fsm = WizardStateFSM()
    assert fsm.step == ProvisionStep.WELCOME
    assert fsm.device is None
    assert fsm.variant is None
    assert fsm.combo is None
    assert fsm.pkg_atoms == []
    assert fsm.prepared is None
    assert fsm.host_blkdev_map == {}
    assert fsm.host_blkdev_fingerprints == {}


def test_fsm_step_changed_observer() -> None:
    fsm = WizardStateFSM()
    events: list[StateChangedEvent] = []
    fsm.add_observer(events.append)

    fsm.step = ProvisionStep.DEVICE
    assert len(events) == 1
    assert isinstance(events[0], StepChangedEvent)
    assert events[0].step == ProvisionStep.DEVICE

    # Re-setting same step does not emit
    fsm.step = ProvisionStep.DEVICE
    assert len(events) == 1


def test_fsm_cascade_invalidation_device_to_variant() -> None:
    fsm = WizardStateFSM()
    events: list[StateChangedEvent] = []
    fsm.add_observer(events.append)

    dummy_device = DeviceChoice(id="d1", display_name="Device 1")
    dummy_variant = VariantChoice(id="v1", display_name="Variant 1")

    fsm._variant = dummy_variant

    fsm.device = dummy_device
    assert fsm.device == dummy_device
    assert fsm.variant is None

    # Events emitted: device changed, then cascading invalidations (variant, combo, pkg_atoms, prepared, host_blkdev_map, host_blkdev_fingerprints)
    property_events = [e for e in events if isinstance(e, PropertyChangedEvent)]
    names = [e.property_name for e in property_events]
    assert names[:2] == ["device", "variant"]
    assert "combo" in names
    assert property_events[0].value == dummy_device
    assert property_events[1].value is None


def test_fsm_cascade_invalidation_variant_to_combo() -> None:
    fsm = WizardStateFSM()
    events: list[StateChangedEvent] = []
    fsm.add_observer(events.append)

    dummy_variant = VariantChoice(id="v1", display_name="Variant 1")
    dummy_combo = ComboChoice(id="c1", display_name="Combo 1")

    fsm._combo = dummy_combo

    fsm.variant = dummy_variant
    assert fsm.variant == dummy_variant
    assert fsm.combo is None

    property_events = [e for e in events if isinstance(e, PropertyChangedEvent)]
    names = [e.property_name for e in property_events]
    assert names[:2] == ["variant", "combo"]


def test_fsm_cascade_invalidation_combo_clears_prepared_and_storage() -> None:
    fsm = WizardStateFSM()
    dummy_combo = ComboChoice(id="c1", display_name="Combo 1")
    prepared = PreparedProvision(strategies=[], pkg_part_maps={})
    fsm.pkg_atoms = ["pkg1"]
    fsm.prepared = prepared
    fsm.host_blkdev_map = {"disk": "/dev/sdb"}
    fsm.host_blkdev_fingerprints = {"disk": "fp1"}

    events: list[StateChangedEvent] = []
    fsm.add_observer(events.append)

    fsm.combo = dummy_combo
    assert fsm.combo == dummy_combo
    assert fsm.pkg_atoms == []
    assert fsm.prepared is None
    assert fsm.host_blkdev_map == {}
    assert fsm.host_blkdev_fingerprints == {}


def test_fsm_direct_property_setters() -> None:
    fsm = WizardStateFSM()
    events: list[StateChangedEvent] = []
    fsm.add_observer(events.append)

    atoms = ["atom1", "atom2"]
    fsm.pkg_atoms = atoms
    assert fsm.pkg_atoms == atoms

    prepared = PreparedProvision(strategies=[], pkg_part_maps={})
    fsm.prepared = prepared
    assert fsm.prepared == prepared

    blk_map = {"disk": "/dev/sda"}
    fsm.host_blkdev_map = blk_map
    assert fsm.host_blkdev_map == blk_map

    fps = {"disk": "fp_hash"}
    fsm.host_blkdev_fingerprints = fps
    assert fsm.host_blkdev_fingerprints == fps

    property_names = [
        e.property_name for e in events if isinstance(e, PropertyChangedEvent)
    ]
    assert property_names == [
        "pkg_atoms",
        "prepared",
        "host_blkdev_map",
        "host_blkdev_fingerprints",
    ]
