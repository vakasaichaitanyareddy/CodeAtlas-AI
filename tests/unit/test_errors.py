import pytest
from apps.api.app.core.errors import APIError, create_error_response


def test_api_error_initialization():
    err = APIError(
        message="Resource not found.",
        code="RESOURCE_NOT_FOUND",
        status_code=404,
        details={"resource": "repository", "id": "123"},
    )
    assert err.message == "Resource not found."
    assert err.code == "RESOURCE_NOT_FOUND"
    assert err.status_code == 404
    assert err.details["resource"] == "repository"


def test_create_error_response():
    resp = create_error_response(
        message="Unauthorized access",
        code="UNAUTHORIZED",
        status_code=401,
        request_id="req-999",
        details={"reason": "expired"},
    )
    assert resp.status_code == 401
    import json
    body = json.loads(resp.body.decode("utf-8"))
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Unauthorized access"
    assert body["error"]["request_id"] == "req-999"
    assert body["error"]["details"]["reason"] == "expired"
