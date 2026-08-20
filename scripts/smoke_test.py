#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from typing import Any
from urllib.request import Request, urlopen


def request_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit local smoke target
        return json.load(response)


def read_initial_sse_snapshot(url: str) -> dict[str, Any]:
    request = Request(url, method="GET")
    with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit local smoke target
        event_name = None
        for raw_line in response:
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            elif line.startswith("data: ") and event_name == "session.snapshot":
                return json.loads(line.removeprefix("data: "))
    raise RuntimeError("SSE stream closed before the initial snapshot")


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
    health = request_json(f"{base}/healthz")
    assert health["ok"] is True
    assert health["database"] == "ok"
    print("health", health)

    session = request_json(
        f"{base}/api/sessions",
        "POST",
        {"prompt": "a smoke-tested evolving machine garden", "seed": 20260820},
    )
    session_id = session["session_id"]
    streamed = read_initial_sse_snapshot(f"{base}/api/sessions/{session_id}/events")
    assert streamed["session_id"] == session_id
    print("session", session_id)

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        session = request_json(f"{base}/api/sessions/{session_id}")
        candidates = (session.get("active_round") or {}).get("candidates", [])
        if len(candidates) == 4 and all(candidate["status"] == "ready" for candidate in candidates):
            break
        time.sleep(0.2)
    else:
        raise SystemExit("candidate round did not become ready")

    chosen = candidates[0]
    exposed = [candidate["candidate_id"] for candidate in candidates]
    session = request_json(
        f"{base}/api/sessions/{session_id}/candidates/{chosen['candidate_id']}/commit",
        "POST",
        {
            "request_id": "command_smoke_commit_0001",
            "exposed_candidate_ids": exposed,
            "expected_mutation_version": session["mutation_version"],
        },
    )
    assert session["learner"]["observation_count"] == 1

    design_id = session["current_design"]["design_id"]
    session = request_json(
        f"{base}/api/sessions/{session_id}/designs/{design_id}/favorite",
        "POST",
        {
            "request_id": "command_smoke_favorite_0001",
            "favorite": True,
        },
    )
    assert design_id in session["favorites"]

    duplicate = request_json(
        f"{base}/api/sessions/{session_id}/designs/{design_id}/favorite",
        "POST",
        {
            "request_id": "command_smoke_favorite_0001",
            "favorite": True,
        },
    )
    assert duplicate == session
    print("commit", design_id)
    print("atlas modes", session["atlas"]["component_count"])
    print("smoke test passed")


if __name__ == "__main__":
    main()
