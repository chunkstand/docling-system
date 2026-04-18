from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.search import SearchFeedbackCreateRequest
from app.services.search_history import get_search_request_detail, record_search_feedback
from app.services.search_replays import get_search_replay_run_detail


class MissingRowSession:
    def get(self, model, key):
        return None


class ExistingRequestSession:
    def get(self, model, key):
        return SimpleNamespace(id=key)


def test_get_search_request_detail_returns_structured_not_found_error() -> None:
    search_request_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        get_search_request_detail(MissingRowSession(), search_request_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "search_request_not_found"
    assert exc_info.value.detail["context"]["search_request_id"] == str(search_request_id)


def test_record_search_feedback_requires_result_rank_with_error_code() -> None:
    search_request_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        record_search_feedback(
            ExistingRequestSession(),
            search_request_id,
            SearchFeedbackCreateRequest(feedback_type="relevant"),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "result_rank_required"


def test_get_search_replay_run_detail_returns_structured_not_found_error() -> None:
    replay_run_id = uuid4()

    with pytest.raises(HTTPException) as exc_info:
        get_search_replay_run_detail(MissingRowSession(), replay_run_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "search_replay_run_not_found"
    assert exc_info.value.detail["context"]["replay_run_id"] == str(replay_run_id)
