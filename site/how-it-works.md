---
title: How it works
---

# How it works

The whole story, from a prompt to an eval verdict, in three sections. Each
section hides the previous section's "out there" complexity and collapses it
to one block.

## How agents work

A prompt goes to an agent, which talks to an inference server, which runs a
model:

```mermaid
flowchart LR
  P[prompt] --> A[agent]
  A --> S[inference server]
  S --> M[model]
```

Add tools, a loop, and planning:

```mermaid
flowchart LR
  P[prompt] --> A[agent]
  A -->|tool call| T[tools]
  T -->|result| A
  A --> R[response]
```

Running locally, the same shape: Pi is the agent, oMLX serves Ornith 1.5 9B.

```mermaid
flowchart LR
  Pi[Pi] --> oMLX[oMLX server]
  oMLX --> O[Ornith 1.5 9B]
```

## How the Engine works

Pi is the coding agent; the server and model collapse to one block:

```mermaid
flowchart LR
  Pi[Pi - coding agent] --> H[server + model]
```

Add guards — the loop breaker, writable-path scope, symbol preservation, and
command bounds:

```mermaid
flowchart LR
  Pi[Pi] --> G[guards]
  G --> H[server + model]
```

Add `/implement`, at a high level: derive a contract, then deliver:

```mermaid
flowchart LR
  I[/implement/] --> D1[derive]
  D1 --> D2[deliver]
  D2 --> C[candidate + receipt]
```

The Engine's pieces: a Python core runs a fresh Pi subprocess, guards loaded,
in its own isolated worktree:

```mermaid
flowchart TB
  E[satyrn-engine - Python] --> P[Pi subprocess, guards loaded]
  P --> W[isolated worktree]
```

Worktree isolation and the logical pieces inside:

```mermaid
flowchart LR
  A[adapter, TypeScript] --> E[engine core, Python]
  E --> W[worktree isolation]
  E --> R[receipt]
```

## How Evals works

The logical pieces of the eval system, in the glossary's words:

```mermaid
flowchart TB
  L[launcher] --> C[cell: isolated workspace]
  C --> A[arm: attempt command]
  A --> T[transcript + patch]
  T --> G[grade: oracle]
  G --> V[verdict]
```

The *physical* run — how the launcher makes the workspace and runs the model
as a subprocess — is on the [Architecture](evals-architecture.md) page.
