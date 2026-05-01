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

@pytest.mark.asyncio
async def test_stream_live_output(runtime):
    """stream() yields new output from the queue as it arrives."""
    sess = await runtime.spawn()
    await runtime.write(sess.id, "echo stream-test\n")
    # Wait for output to arrive
    import asyncio
    await asyncio.sleep(0.3)
    chunks = []
    async for chunk in runtime.stream(sess.id):
        chunks.append(chunk)
        break  # one chunk is enough to prove the queue works
    assert any("stream-test" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_full_output_yields_existing_buffer(runtime):
    """stream(full_output=True) yields existing buffer first."""
    sess = await runtime.spawn()
    await runtime.write(sess.id, "echo partial\n")
    import asyncio
    await asyncio.sleep(0.3)
    assert "partial" in sess.buffer  # confirm buffer has data
    chunks = []
    async for chunk in runtime.stream(sess.id, full_output=True):
        chunks.append(chunk)
        break
    # full_output=True must include existing buffer
    assert any("partial" in c for c in chunks)


@pytest.mark.asyncio
async def test_stream_ends_after_close(runtime):
    """stream() terminates after session is closed."""
    sess = await runtime.spawn()
    await runtime.write(sess.id, "echo done\n")
    import asyncio
    await asyncio.sleep(0.3)
    await runtime.close(sess.id)
    chunks = []
    async for chunk in runtime.stream(sess.id):
        chunks.append(chunk)
    # session closed — no error, chunks collected
    assert sess.status == "closed"
