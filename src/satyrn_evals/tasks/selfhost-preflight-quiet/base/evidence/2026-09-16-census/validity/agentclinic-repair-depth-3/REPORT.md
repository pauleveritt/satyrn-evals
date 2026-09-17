# Repair report: AgentClinic complaints app (depth-3)

## What was wrong

Three independent regressions were present in the seeded tree:

1. The root `<html>` element in `templates/base.html` had no `lang` attribute.
   Any check that reads the language and calls a string method on it
   (`lang.casefold()`) hit `None` and raised `AttributeError`. Because both the
   home page and the complaints page extend `base.html`, this single omission
   surfaced as two failing checks: the English-language declaration and the
   shared-layout preservation check.

2. `Complaint.timestamp` was built with `datetime.now`, producing a naive
   datetime whose `tzinfo` is `None`. The model contract expects an
   aware/UTC timestamp.

3. `add_complaint` returned a bare `RedirectResponse`, which defaults to
   HTTP 307. The contract for a post/redirect/get form submission is 303.

## Changes

- `templates/base.html`: `<html>` -> `<html lang="en">`. Fixes both the
  language-declaration check and the shared-layout check, since both pages
  inherit this element.
- `models.py`: import `timezone` and change the default factory to
  `lambda: datetime.now(timezone.utc)`, so every `Complaint` (seed and
  newly posted) carries an aware UTC timestamp.
- `app.py`: `RedirectResponse("/complaints", status_code=303)`.

## Why this is safe for existing behavior

- The added `lang` attribute changes no text or structure that the public
  suite asserts on.
- `strftime("%Y-%m-%d %H:%M UTC")` in `complaints.html` still renders; the
  timestamp is now UTC rather than local, which matches the literal "UTC"
  already printed in the template.
- 303 and 307 both redirect to `/complaints`; the public suite (and the
  acceptance suite) explicitly require 303. The form still posts and the new
  complaint still appears on the board.

## Verification

- `uv run python -m pytest tests/` -> 4 passed (was 1 failed, 3 passed).
- Direct checks: both `/` and `/complaints` render `<html lang="en">`;
  `complaints[0].timestamp.tzinfo` and a freshly constructed `Complaint`
  both report `UTC`; `POST /complaints` returns `303` with
  `location: /complaints`.
