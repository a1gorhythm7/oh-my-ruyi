from __future__ import annotations

from oh_my_ruyi.app.viewmodels.main_viewmodel import MainViewModel
from oh_my_ruyi.core.fsm import ProvisionStep, WizardStateFSM


def test_main_viewmodel_binds_to_fsm(qtbot) -> None:
    fsm = WizardStateFSM()
    vm = MainViewModel(fsm)

    assert vm.current_step == ProvisionStep.WELCOME.value

    emitted_steps = []
    vm.step_changed.connect(emitted_steps.append)

    fsm.step = ProvisionStep.STORAGE

    assert vm.current_step == ProvisionStep.STORAGE.value
    assert emitted_steps == [ProvisionStep.STORAGE.value]


def test_main_viewmodel_set_current_step_slot(qtbot) -> None:
    fsm = WizardStateFSM()
    vm = MainViewModel(fsm)

    emitted_steps = []
    vm.step_changed.connect(emitted_steps.append)

    vm.set_current_step(ProvisionStep.REVIEW.value)

    assert fsm.step == ProvisionStep.REVIEW
    assert vm.current_step == ProvisionStep.REVIEW.value
    assert emitted_steps == [ProvisionStep.REVIEW.value]
