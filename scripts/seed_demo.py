#!/usr/bin/env python3
"""
Drive a full demo: multi-turn interview + oneshot contradiction / DND / life-event.

Usage (API must already be running on BASE_URL):
  python scripts/seed_demo.py
  python scripts/seed_demo.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx

DEFAULT_BASE = "http://127.0.0.1:8000"
AGENT_ID = "agt_demo"
AGENT_NAME = "Demo Agent"


def _pp(label: str, data: Any) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(data, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a URIE demo agent via the live API")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--agent-id", default=AGENT_ID)
    parser.add_argument("--agent-name", default=AGENT_NAME)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    with httpx.Client(base_url=base, timeout=30.0) as client:
        health = client.get("/v1/health")
        health.raise_for_status()
        print(f"API healthy at {base}")

        tok = client.post(
            "/v1/auth/token",
            json={"agent_id": args.agent_id, "name": args.agent_name},
        )
        tok.raise_for_status()
        token = tok.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        _pp("token", {"agent_id": args.agent_id, "token_prefix": token[:16] + "…"})

        # ── Multi-turn interview ──────────────────────────────────────────
        r0 = client.post("/v1/debriefs", headers=headers, json={"mode": "interview"})
        r0.raise_for_status()
        d0 = r0.json()
        _pp("0. interview opened", {"session_id": d0["session_id"], "next_question": d0.get("next_question"), "status": d0["status"]})
        assert d0["status"] == "interviewing", d0
        assert d0.get("next_question"), d0
        sid = d0["session_id"]

        turns = [
            "Met with John today. John's budget is around 3 million USD.",
            "John's wife is expecting a baby.",
            "Don't contact John until 2026-07-28 — high workload this week.",
        ]
        for i, text in enumerate(turns, start=1):
            rt = client.post(
                f"/v1/debriefs/{sid}/turn",
                headers=headers,
                json={"text": text},
            )
            rt.raise_for_status()
            dt = rt.json()
            _pp(f"0.{i} turn → {dt['status']}", {
                "next_question": dt.get("next_question"),
                "pending_challenge": bool(dt.get("pending_challenge")),
                "turns": len(dt.get("turns") or []),
            })
            if dt["status"] == "awaiting_resolution":
                # Unlikely on first budget; if it happens, resolve and continue
                rr = client.post(
                    f"/v1/debriefs/{sid}/resolve",
                    headers=headers,
                    json={
                        "resolution_note": "Confirmed with client.",
                        "accepted_value": (dt.get("pending_challenge") or {}).get("candidate_value"),
                    },
                )
                rr.raise_for_status()
                dt = rr.json()
                _pp(f"0.{i}b resolved", {"status": dt["status"], "next_question": dt.get("next_question")})
            if dt["status"] == "completed":
                break

        if dt["status"] == "interviewing":
            fin = client.post(f"/v1/debriefs/{sid}/finish", headers=headers, json={})
            fin.raise_for_status()
            _pp("0.finished", fin.json())

        # ── One-shot contradiction challenge ──────────────────────────────
        r2 = client.post(
            "/v1/debriefs",
            headers=headers,
            json={
                "mode": "oneshot",
                "transcript": "Update on John — John's budget is 5 million USD now.",
            },
        )
        r2.raise_for_status()
        d2 = r2.json()
        _pp("2. contradiction (awaiting resolution)", d2)
        assert d2["status"] == "awaiting_resolution", d2
        assert d2.get("pending_challenge"), d2

        r2r = client.post(
            f"/v1/debriefs/{d2['session_id']}/resolve",
            headers=headers,
            json={
                "resolution_note": "His bonus came through and his spouse agreed to stretch.",
                "accepted_value": {"amount": 5_000_000, "currency": "USD"},
            },
        )
        r2r.raise_for_status()
        d2r = r2r.json()
        _pp("2b. conflict resolved", d2r)
        assert d2r["status"] == "completed", d2r

        # Feed (include held)
        feed = client.get("/v1/feed", headers=headers, params={"include_held": True})
        feed.raise_for_status()
        items = feed.json()
        _pp("feed (active + held)", items)

        nodes = client.get("/v1/nodes", headers=headers, params={"kind": "Person"})
        nodes.raise_for_status()
        _pp("clients", nodes.json())

        print("\nSeed demo complete.")
        print(f"Open the UI at {base}/ and sign in as agent_id={args.agent_id}")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except httpx.HTTPError as exc:
        print(f"HTTP error: {exc}", file=sys.stderr)
        if getattr(exc, "response", None) is not None:
            print(exc.response.text, file=sys.stderr)
        raise SystemExit(1)
