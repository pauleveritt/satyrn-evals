---
orphan: true
---

# What actually happens when an agent works

You just ran a single command and got a `pass` verdict back. Behind that one
command sits a loop you did not have to think about. This page names the pieces
of that loop in plain language, so the rest of the docs can refer to them by
name.

## You give a task

The loop starts with a person and a task. In the tutorial that task was
"grade this bundled change"; in real use it is "change this code to do X."
This is the *Developer's task* card in the diagram below: a goal written in
plain words, plus the code it applies to. Everything else exists to serve
that card.

## The agent

You do not talk to the model directly. You hand the task to an *agent*, a
program that sits between you and the model and decides what to do next.
Hugging Face's Agents Course defines the role this way:

> An Agent is a system that uses an AI Model, typically an LLM, as its core reasoning engine. It understands natural language, reasons and plans to solve problems, and interacts with its environment by gathering information and taking actions.

That is the *Coding agent* card: it reads your task, thinks in plain language,
and decides which actions to take. (Hugging Face Agents Course, *What are
agents?* — `units/en/unit1/what-are-agents.mdx`;
<https://huggingface.co/learn/agents-course/unit1/what-are-agents>.)

## Why tools exist

The model only emits text. When it wants to run a test or read a file, it says
so in words, and something else has to do the actual work. That something is a
*tool*, and the agent is the interpreter:

> The Agent interprets the LLM's text-based tool invocation, executes the specified tool on the LLM's behalf, and retrieves the results.

The *Tools* card is the set of actions the agent can take on your behalf —
run a command, read a file, edit code — and the *Codebase* card is the
project those actions touch. (Hugging Face Agents Course, *What are tools?* —
`units/en/unit1/tools.mdx`;
<https://huggingface.co/learn/agents-course/unit1/tools>.)

## The serving layer

The model itself runs inside a separate program, an *inference server*, which
loads the model, runs inference, and exposes an OpenAI-compatible API. The
agent sends it a request — "given this conversation, what comes next?" — and
the server returns the next tokens the model produces.

This split between a client that asks and a server that answers is standard.
NVIDIA NIM's overview describes the server as a container that loads models,
runs inference, and exposes an OpenAI-compatible API, and vLLM's architecture
overview draws the same line between the engine that runs the model and the
front-end that takes requests. (NVIDIA NIM, *Architecture at a Glance* —
<https://docs.nvidia.com/nim/large-language-models/latest/introduction.html>;
vLLM, *Architecture overview* —
<https://docs.vllm.ai/en/stable/design/arch_overview>.)

```{figure} diagrams/agent-big-picture.svg
:alt: A coding agent uses tools and a codebase, and exchanges requests and generated tokens with an inference server that runs the model.
```

The figure lays the five cards on top of each other: your task drives the
agent, the agent drives its tools and the codebase, and the agent talks to the
server that runs the model.

## On a laptop with 16–32 GB

Where the server and the model live depends on your hardware, not on the
picture. On a laptop with 16–32 GB of RAM the server and the model can run
locally, and RAM bounds which model fits. On a remote server they run
remotely, and the network takes the place the RAM held: instead of "will it
fit in memory?" you ask "can I reach it?" The diagram is the same either way —
the agent still sends a request and the server still returns tokens.

## You already ran this loop

The tutorial's verdict was produced by an *attempt command*, and that command
is this whole loop treated as one program. It took the task, drove the agent,
ran the tools against the codebase, and talked to the model through a serving
layer, then returned the result. The [guides](guides/index.md) show how to
point that same loop at your own tasks.

Evals never looks inside the loop. It hands the loop a task, waits for it to
finish, and grades the saved change afterward. The loop is a boundary, and
everything in these docs sits on one side of it or the other.
