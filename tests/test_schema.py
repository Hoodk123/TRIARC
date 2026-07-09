from orchestrator.schema import Capability, Privacy, Task


def test_task_defaults():
    task = Task(goal="add JWT auth", capability_required=Capability.CODE_COMPLEX)

    assert task.task_id
    assert task.constraints.privacy == Privacy.LOCAL
    assert task.confidence == 0.0
    assert task.result is None
    assert task.escalation_reason is None


def test_task_roundtrips_through_json():
    task = Task(goal="classify this", capability_required=Capability.ROUTE)

    restored = Task.model_validate_json(task.model_dump_json())

    assert restored == task
