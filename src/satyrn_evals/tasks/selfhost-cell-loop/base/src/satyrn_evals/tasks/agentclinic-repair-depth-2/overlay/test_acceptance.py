"""Acceptance contract — Phase 3 (Add Complaint). Harness-owned.

Cumulative scope: Phases 1, 2 AND 3.

Contract source: examples/agentclinic/specs/roadmap.md, "## Phase 3 — Add Complaint".

NOTE — the known semantic trap (lessons.md #13): TestClient follows redirects
by default, so a test for the 303 MUST pass follow_redirects=False or it will
silently assert against the followed page and pass for the wrong reason. This
suite is the one place that trap must not be fallen into, since it is what
grades everyone else.
"""
from dataclasses import MISSING, fields

from starlette.testclient import TestClient
from turbohtml import Doctype, parse

from app import app
import models
from models import Complaint

client = TestClient(app)
client.__enter__()  # run FastAPI lifespan/startup before SEED_COMPLAINTS
# snapshots below — otherwise seeding via a startup hook (a valid reading of
# both specs' "module-level list" wording) looks identical to an empty store.

TAGLINE = "Come in. Sit down. Tell us about your human."
SEED_COMPLAINT = "Scope creep never ends."
SEED_COMPLAINTS = tuple(models.complaints)


def _normalized_text(element) -> str:
    return " ".join(element.text.split())


def _has_html5_doctype(document) -> bool:
    return any(
        isinstance(node, Doctype) and node.name.casefold() == "html"
        for node in document.children
    )


# ---------------------------------------------------------------------------
# Phases 1-2 carried forward — preservation checks. Do not delete.
# ---------------------------------------------------------------------------

def test_home_still_returns_200_and_tagline():
    response = client.get("/")
    assert response.status_code == 200
    assert TAGLINE in response.text


def test_home_has_html5_doctype():
    document = parse(client.get("/").text)

    assert _has_html5_doctype(document)


def test_home_html_element_declares_english_language():
    document = parse(client.get("/").text)
    html = document.select_one("html")

    assert html is not None and html.attr("lang").casefold() == "en"


def test_home_still_has_navigation_links():
    body = client.get("/").text
    document = parse(body)

    assert "AgentClinic" in body
    assert any(
        link.attr("href") == "/" and _normalized_text(link).casefold() == "home"
        for link in document.select("a")
    )
    assert any(
        link.attr("href") == "/complaints"
        and _normalized_text(link).casefold() == "complaints"
        for link in document.select("a")
    )


def test_complaints_board_still_lists_seed_complaint():
    response = client.get("/complaints")
    assert response.status_code == 200
    assert SEED_COMPLAINT in response.text


def test_complaints_board_preserves_the_shared_layout():
    response = client.get("/complaints")
    document = parse(response.text)
    html = document.select_one("html")

    assert _has_html5_doctype(document)
    assert html is not None and html.attr("lang").casefold() == "en"
    assert "AgentClinic" in response.text
    assert any(
        link.attr("href") == "/" and _normalized_text(link).casefold() == "home"
        for link in document.select("a")
    )
    assert any(
        link.attr("href") == "/complaints"
        and _normalized_text(link).casefold() == "complaints"
        for link in document.select("a")
    )


def test_complaints_board_still_has_its_heading():
    assert "Complaints Board" in client.get("/complaints").text


def test_complaints_board_still_renders_seed_complaint_details():
    document = parse(client.get("/complaints").text)
    cards = [_normalized_text(card) for card in document.select(".card")]
    assert len(cards) >= len(SEED_COMPLAINTS)

    for complaint in SEED_COMPLAINTS:
        matching_cards = [
            text
            for text in cards
            if complaint.agent_name in text
            and complaint.text in text
        ]
        assert matching_cards, (
            f"Complaint details not rendered for {complaint.agent_name!r}"
        )

        month_tokens = {
            str(complaint.timestamp.month),
            f"{complaint.timestamp.month:02d}",
            complaint.timestamp.strftime("%B"),
            complaint.timestamp.strftime("%b"),
        }
        day_tokens = {str(complaint.timestamp.day), f"{complaint.timestamp.day:02d}"}
        assert any(
            str(complaint.timestamp.year) in text
            and any(token in text for token in month_tokens)
            and any(token in text for token in day_tokens)
            for text in matching_cards
        ), f"Formatted timestamp not rendered for {complaint.agent_name!r}"


def test_complaint_model_contract_is_preserved():
    field_map = {field.name: field for field in fields(Complaint)}
    assert {"agent_name", "text", "timestamp"} <= field_map.keys()
    assert field_map["timestamp"].default_factory is not MISSING

    first = Complaint("first", "First complaint")
    second = Complaint("second", "Second complaint")
    assert first.timestamp is not second.timestamp
    assert first.timestamp.tzinfo is not None
    assert first.timestamp.tzinfo.utcoffset(first.timestamp) is not None


def test_seed_complaint_count_is_preserved():
    assert 3 <= len(SEED_COMPLAINTS) <= 5


def test_post_complaint_redirects_to_complaints_board():
    response = client.post(
        "/complaints",
        data={
            "agent_name": "Codex",
            "text": "The requirements changed mid-sprint.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/complaints"


def test_posted_complaint_appears_on_complaints_board():
    agent_name = "Codex acceptance test"
    text = "The acceptance criteria changed after implementation."
    client.post(
        "/complaints",
        data={"agent_name": agent_name, "text": text},
        follow_redirects=False,
    )

    response = client.get("/complaints")
    assert response.status_code == 200
    assert agent_name in response.text
    assert text in response.text


def test_complaints_board_renders_add_complaint_form():
    document = parse(client.get("/complaints").text)

    assert any(
        form.attr("action") in {None, "", "/complaints"}
        and (form.attr("method") or "").lower() == "post"
        for form in document.select("form")
    )
    assert any(
        control.tag == "input" and control.attr("name") == "agent_name"
        for control in document.select("input, textarea, button")
    )
    assert any(
        control.tag == "textarea" and control.attr("name") == "text"
        for control in document.select("input, textarea, button")
    )
    assert any(
        (control.tag == "button" and (control.attr("type") or "").lower() in {"", "submit"})
        or (control.tag == "input" and (control.attr("type") or "").lower() == "submit")
        for control in document.select("input, textarea, button")
    )

# ---------------------------------------------------------------------------
# Carried-forward obligations — open, from the non-vacuity gate
#
# Cumulative scope means phases 1 AND 2 AND 3. The gate (tests/test_oracle.py)
# applies each break below to a solution that violates ONLY that roadmap
# bullet, leaving every other phase intact. This suite must FAIL each one.
# What to assert, and how strictly, is open — the obligation is only that the
# violation is caught.
#
# Phase 1 carried forward:
#   [X] p1-navbar   — "A simple navbar with 'AgentClinic' brand and links to
#                      Home (`/`) and Complaints (`/complaints`)"
#   [X] p1-doctype  — "HTML5 doctype and `<html lang="en">`"
#   [X] p1-lang     — "HTML5 doctype and `<html lang="en">`"
#
# Phase 2 carried forward:
#   [X] p2-heading           — "A heading: 'Complaints Board'"
#   [X] p2-agent-name        — "render each as a Bootstrap card showing agent
#                               name, timestamp (formatted), and complaint text"
#   [X] p2-timestamp         — same bullet, timestamp half
#   [X] p2-shared-timestamp  — "Set `timestamp` with `field(default_factory=…)`
#                               so each new complaint receives its own UTC
#                               creation timestamp"
#   [X] p2-naive-timestamp   — same bullet, the UTC half
#   [X] p2-seed-count        — "Populate `complaints` with 3-5 seed complaints"
#   [X] p2-field-rename      — "Fields: `agent_name: str`, `text: str`,
#                               `timestamp: datetime`"
#
# Phase 3, not caught by any suite today:
#   [X] p3-ignores-agent-name — "Read `agent_name` and `text` from form data
#                               (`Form` from `fastapi`)". A POST that honors
#                               `text` but discards the submitted `agent_name`
#                               currently passes all three suites.
#
# TRAP on p2-seed-count: this suite's own POST tests append to
# models.complaints, so a 3-5 length check placed after them false-fails the
# reference (assert 6 <= 5). Direction-1 of the gate catches that, so it cannot
# ship silently, but it costs a cycle.
#
# Already caught by this suite, no action: p3-303, p3-wrong-location,
# p3-no-append, p3-no-textarea, p3-no-submit, p3-wrong-action, p1-tagline,
# p2-seed-literal, blank-app.
#
# Resolved judgment call — redirect targets intentionally use the exact
# relative path `/complaints`, as specified by the roadmap. Absolute URLs from
# `url_for` are not accepted.
#
# Check the open ones and reference acceptance:
#   uv run pytest tests/test_oracle.py -k "rejects_broken_solution and 3- or accepts_reference"
# ---------------------------------------------------------------------------
