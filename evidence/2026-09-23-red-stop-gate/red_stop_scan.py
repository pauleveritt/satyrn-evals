"""Offline estimate for the red-stop gate.

Counts recorded Engine cells that ended on a turn with no tool call while the
last self-test at the current mutation generation was red: the case the
completion gate at satyrn-engine ``78ab87d`` let through, because it only
checked *whether* a self-test had run since the last landed edit or write.

Generations are reconstructed from landed ``edit``/``write`` tool results;
self-test outcomes from ``self_test`` results, the Engine's detected-run
sentence, and ``self_test_enforced`` entries. Run from the repository root:

    uv run python evidence/2026-09-23-red-stop-gate/red_stop_scan.py
"""

import json
import re
from pathlib import Path

RUNS = Path.home() / "satyrn-runs"
DETECTED = "The Engine also ran self_test"


def _events(path: Path):
    for line in path.read_text(errors="ignore").splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            continue


def _text(message: dict) -> str:
    return "".join(c.get("text", "") for c in message.get("content", []) if isinstance(c, dict))


def _passed(text: str) -> bool:
    segment = text.split(DETECTED, 1)[-1]
    if exited := re.search(r"Test command exited (\d+)", segment):
        return exited.group(1) == "0"
    return not re.search(r"\bfailed\b|FAILED|timed out", segment)


def scan(path: Path) -> dict | None:
    generation = 0
    last: tuple[int, bool] | None = None  # (generation, passed)
    calls: dict[str, str] = {}
    final = None
    for event in _events(path):
        kind = event.get("type")
        if kind == "entry_appended":
            entry = event.get("entry", {})
            if entry.get("customType") == "self_test_enforced":
                data = entry.get("data", {})
                last = (data.get("generation"), data.get("exit_code") == 0)
        if kind != "message_end":
            continue
        message = event["message"]
        role = message.get("role")
        if role == "assistant":
            for part in message.get("content", []):
                if part.get("type") == "toolCall":
                    calls[part["id"]] = part["name"]
            final = message
        elif role == "toolResult":
            name = calls.get(message.get("toolCallId"), message.get("toolName"))
            text = _text(message)
            landed = not message.get("isError") and not text.lower().startswith("refused")
            if name in ("write", "edit") and landed:
                generation += 1
            if name == "self_test" or DETECTED in text:
                last = (generation, _passed(text))
    if final is None:
        return None
    no_call = final.get("stopReason") not in ("error", "aborted", "length") and not any(
        part.get("type") == "toolCall" for part in final.get("content", [])
    )
    red_stop = no_call and last is not None and last[0] == generation and not last[1]
    return {"final_no_call": no_call, "generation": generation, "last": last, "red_stop": red_stop}


def main() -> None:
    rows = []
    for deliver in sorted(RUNS.glob("*/engine/*/engine-deliver.txt")):
        cell = deliver.parent
        facts = scan(deliver)
        if facts is None:
            continue
        attempt = cell / "attempt.json"
        receipt = cell / "engine-receipt.json"
        verdict = json.loads(attempt.read_text()).get("verdict") if attempt.exists() else None
        engine_code = json.loads(receipt.read_text()).get("code") if receipt.exists() else None
        rows.append((str(cell.relative_to(RUNS)), facts, verdict, engine_code))
    print("engine cells scanned:", len(rows))
    print("ended on a no-call turn:", sum(r[1]["final_no_call"] for r in rows))
    hits = [r for r in rows if r[1]["red_stop"]]
    print("red stop (last self-test red at the current generation):", len(hits))
    for name, facts, verdict, engine_code in hits:
        print(f"  {name} | graded {verdict} | engine receipt {engine_code} | last {facts['last']}")


if __name__ == "__main__":
    main()
