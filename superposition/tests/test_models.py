import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from superposition.db import AsyncSessionLocal
from superposition.models import Project, Task, Artifact

@pytest.mark.asyncio
async def test_create_project():
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

        # Retrieve by id
        result = await session.get(Project, project.id)
        assert result is not None
        assert result.title == "Test Project"

        # Cleanup
        await session.delete(result)
        await session.commit()

@pytest.mark.asyncio
async def test_create_task_with_project():
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

        # Cleanup
        await session.delete(fetched_task)
        await session.delete(project)
        await session.commit()
