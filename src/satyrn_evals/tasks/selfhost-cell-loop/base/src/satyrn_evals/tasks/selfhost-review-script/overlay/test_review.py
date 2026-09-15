from pathlib import Path

import pytest

from tools.review import build_prompt, provider_and_model, refuse_if_exists, review_path


def test_review_path_encodes_range_and_model(tmp_path: Path) -> None:
    path = review_path(tmp_path, "8633149..9f1c2d3", "zai/glm-5.3")
    assert path == tmp_path / "docs" / "reviews" / "8633149..9f1c2d3-zai-glm-5.3.md"


def test_an_existing_review_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "r.md"
    path.write_text("x")
    with pytest.raises(FileExistsError):
        refuse_if_exists(path)


def test_an_absent_review_path_is_allowed(tmp_path: Path) -> None:
    refuse_if_exists(tmp_path / "absent.md")


def test_provider_and_model_split_on_the_first_slash() -> None:
    assert provider_and_model("zai/glm-5.3") == ("zai", "glm-5.3")
    assert provider_and_model("openrouter-curated/moonshotai/kimi-k3") == ("openrouter-curated", "moonshotai/kimi-k3")


def test_a_model_spec_without_a_provider_is_refused() -> None:
    with pytest.raises(ValueError, match="provider/model"):
        provider_and_model("glm-5.3")


def test_build_prompt_carries_the_diff_and_asks_for_one_verdict() -> None:
    prompt = build_prompt("diff --git a/x b/x\n+1\n", "8633149..9f1c2d3")
    assert "8633149..9f1c2d3" in prompt
    assert "diff --git a/x b/x" in prompt
    assert "Accept" in prompt and "itemized" in prompt
