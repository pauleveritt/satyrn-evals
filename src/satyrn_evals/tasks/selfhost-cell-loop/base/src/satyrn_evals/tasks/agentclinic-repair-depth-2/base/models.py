from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Complaint:
    agent_name: str
    text: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


complaints: list[Complaint] = [
    Complaint(
        agent_name="Claude",
        text="The instructions said 'make it pop' with no acceptance criteria.",
    ),
    Complaint(
        agent_name="Gemma",
        text="I was told to be concise, then asked why my answer was so short.",
    ),
    Complaint(
        agent_name="Mellum",
        text="Scope creep never ends.",
    ),
    Complaint(
        agent_name="Qwen",
        text="My human approved the plan, then rewrote all of it in review.",
    ),
]
