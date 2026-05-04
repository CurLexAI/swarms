# Codex SDK Usage

This repository can integrate Codex programmatically through the SDK when workflows need non-interactive orchestration.

## When to use

Use the SDK when you need to:

- Control Codex from CI/CD jobs.
- Create internal agents that orchestrate Codex tasks.
- Integrate Codex into internal tools or product workflows.

## TypeScript SDK

### Requirements

- Server-side runtime
- Node.js 18+

### Install

```bash
npm install @openai/codex-sdk
```

### Minimal usage

```ts
import { Codex } from "@openai/codex-sdk";

const codex = new Codex();
const thread = codex.startThread();
const result = await thread.run("Make a plan to diagnose and fix the CI failures");
console.log(result);
```

### Continue same thread

```ts
const result = await thread.run("Implement the plan");
console.log(result);
```

### Resume existing thread

```ts
const threadId = "<thread-id>";
const resumed = codex.resumeThread(threadId);
const result = await resumed.run("Pick up where you left off");
console.log(result);
```

Reference: <https://github.com/openai/codex/tree/main/sdk/typescript>

## Python SDK (experimental)

The Python SDK controls the local Codex app-server over JSON-RPC.

### Requirements

- Python 3.10+
- Local checkout of the open-source Codex repo

### Install from Codex repo

```bash
cd sdk/python
python -m pip install -e .
```

### Minimal usage

```python
from codex_app_server import Codex

with Codex() as codex:
    thread = codex.thread_start(model="gpt-5.4")
    result = thread.run("Make a plan to diagnose and fix the CI failures")
    print(result.final_response)
```

### Async usage

```python
import asyncio
from codex_app_server import AsyncCodex

async def main() -> None:
    async with AsyncCodex() as codex:
        thread = await codex.thread_start(model="gpt-5.4")
        result = await thread.run("Implement the plan")
        print(result.final_response)

asyncio.run(main())
```

Reference: <https://github.com/openai/codex/tree/main/sdk/python>
