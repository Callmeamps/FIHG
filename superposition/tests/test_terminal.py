import pytest
import pytest_asyncio
from superposition.terminal import TerminalRuntime


@pytest.fixture
def runtime():
    return TerminalRuntime()


@pytest.mark.asyncio
async def test_spawn_bash(runtime):
    sess = await runtime.spawn()
    assert sess.status == "running"
    assert sess.pid > 0
    assert sess.id in runtime.sessions


@pytest.mark.asyncio
async def test_write_and_read(runtime):
    sess = await runtime.spawn()
    await runtime.write(sess.id, "echo hello\n")
    import asyncio
    await asyncio.sleep(0.3)
    assert "hello" in sess.buffer


@pytest.mark.asyncio
async def test_close_session(runtime):
    sess = await runtime.spawn()
    await runtime.close(sess.id)
    assert sess.status == "closed"


@pytest.mark.asyncio
async def test_resize(runtime):
    sess = await runtime.spawn()
    await runtime.resize(sess.id, 120, 40)
    # No crash is sufficient


@pytest.mark.asyncio
async def test_write_to_closed_session(runtime):
    sess = await runtime.spawn()
    await runtime.close(sess.id)
    with pytest.raises(RuntimeError, match="not running"):
        await runtime.write(sess.id, "data")