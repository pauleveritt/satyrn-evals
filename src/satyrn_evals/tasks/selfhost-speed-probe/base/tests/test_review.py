from pathlib import Path

import pytest

from tools.review import (
    build_prompt,
    normalize_document,
    provider_and_model,
    refuse_if_exists,
    review_path,
)


def test_review_path_encodes_range_and_model(tmp_path: Path) -> None:
    path = review_path(tmp_path, "8633149..9f1c2d3", "zai/glm-5.3")
    assert path == tmp_path / "docs" / "reviews" / "8633149..9f1c2d3-zai-glm-5.3.md"


def test_a_branch_name_range_is_slugged_into_docs_reviews(tmp_path: Path) -> None:
    path = review_path(tmp_path, "feature/x..main", "zai/glm-5.3")
    assert path == tmp_path / "docs" / "reviews" / "feature-x..main-zai-glm-5.3.md"
    assert path.parent == tmp_path / "docs" / "reviews"


def test_an_absolute_looking_range_stays_inside_docs_reviews(tmp_path: Path) -> None:
    path = review_path(tmp_path, "/abs..main", "zai/glm-5.3")
    assert path == tmp_path / "docs" / "reviews" / "-abs..main-zai-glm-5.3.md"
    assert path.parent == tmp_path / "docs" / "reviews"


def test_a_traversal_looking_range_stays_inside_docs_reviews(tmp_path: Path) -> None:
    path = review_path(tmp_path, "../../..", "zai/glm-5.3")
    assert path == tmp_path / "docs" / "reviews" / "..-..-..-zai-glm-5.3.md"
    assert path.parent == tmp_path / "docs" / "reviews"


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


def test_normalize_document_strips_trailing_whitespace_and_blank_eof() -> None:
    dirty = "Accept  \n\n- item file:1\n\n"
    assert normalize_document(dirty) == "Accept\n\n- item file:1\n"


def test_normalize_document_leaves_already_clean_text_unchanged() -> None:
    clean = "Accept\n\n- item file:1\n"
    assert normalize_document(clean) == clean


def test_normalize_document_on_empty_text_does_not_crash() -> None:
    assert normalize_document("") == ""
