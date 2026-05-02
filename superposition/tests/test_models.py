"""Unit + integration tests for models.

Unit tests (test_unit_*) use AsyncSessionLocal directly — model in isolation.
Integration tests (test_integration_*) use get_session fixture — matches app wiring.
"""
import pytest
from superposition.db import AsyncSessionLocal
from superposition.models import Project, Task, Artifact


# --- Unit tests (model in isolation) ---

@pytest.mark.asyncio
async def test_unit_create_project():
    async with AsyncSessionLocal() as session:
        project = Project(
            title="Test Project",
            description="A test project",
            status="active",
            priority=2,
            urgency=2,
            risk=2
        )
        session.add(project)
        await session.commit()

        result = await session.get(Project, project.id)
        assert result is not None
        assert result.title == "Test Project"

        await session.delete(result)
        await session.commit()

@pytest.mark.asyncio
async def test_unit_create_task_with_project():
    async with AsyncSessionLocal() as session:
        project = Project(
            title="Project with Task",
            description="Testing task relationship",
            status="active"
        )
        session.add(project)
        await session.commit()

        task = Task(
            project_id=project.id,
            title="Test Task",
            status="todo",
            priority=2
        )
        session.add(task)
        await session.commit()

        fetched_task = await session.get(Task, task.id)
        assert fetched_task is not None
        assert fetched_task.project_id == project.id

        await session.delete(fetched_task)
        await session.delete(project)
        await session.commit()


# --- Integration tests (use get_session fixture — same as routes) ---

@pytest.mark.asyncio
async def test_integration_project_lifecycle(get_session):
    """Create → retrieve → update → delete through get_session."""
    project = Project(
        title="Integration Project",
        description="Full lifecycle test",
        status="active",
        priority=3,
        urgency=2,
        risk=1,
    )
    get_session.add(project)
    await get_session.flush()  # no explicit commit — get_session auto-commits on success

    result = await get_session.get(Project, project.id)
    assert result is not None
    assert result.title == "Integration Project"

    result.description = "Updated description"
    await get_session.flush()

    reloaded = await get_session.get(Project, result.id)
    assert reloaded.description == "Updated description"

@pytest.mark.asyncio
async def test_integration_task_project_relationship(get_session):
    """Task correctly linked to project via foreign key."""
    project = Project(title="Parent Project", status="active")
    get_session.add(project)
    await get_session.flush()

    task = Task(project_id=project.id, title="Linked Task", status="todo")
    get_session.add(task)
    await get_session.flush()

    fetched = await get_session.get(Task, task.id)
    assert fetched.project_id == project.id
    assert fetched.project.title == "Parent Project"

@pytest.mark.asyncio
async def test_integration_artifact_task_relationship(get_session):
    """Artifact correctly linked to task."""
    project = Project(title="Project for Artifact", status="active")
    get_session.add(project)
    await get_session.flush()

    task = Task(project_id=project.id, title="Artifact Task", status="todo")
    get_session.add(task)
    await get_session.flush()

    artifact = Artifact(
        project_id=project.id,
        task_id=task.id,
        title="Test Artifact",
        kind="output",
    )
    get_session.add(artifact)
    await get_session.flush()

    fetched = await get_session.get(Artifact, artifact.id)
    assert fetched.task_id == task.id
    assert fetched.task.title == "Artifact Task"