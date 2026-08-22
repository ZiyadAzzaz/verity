from __future__ import annotations

import base64
import json

import pytest

from verity.messaging import decode_push_envelope


def test_decode_pubsub_envelope() -> None:
    data = base64.b64encode(json.dumps({"job_id": "abc", "source_url": "x"}).encode()).decode()
    assert decode_push_envelope({"message": {"data": data, "messageId": "m1"}}) == ("abc", "m1")


def test_decode_pubsub_rejects_invalid_data() -> None:
    with pytest.raises(ValueError, match="base64"):
        decode_push_envelope({"message": {"data": "%%%"}})
