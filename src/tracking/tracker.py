"""实验台账：SQLite，exp_id ↔ config_hash ↔ git_commit 三方绑定。失败实验同样归档。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "runs" / "tuner.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
  exp_id        TEXT PRIMARY KEY,
  parent_exp    TEXT,
  kind          TEXT,             -- baseline | candidate | golden
  split         TEXT,
  config_hash   TEXT,
  git_commit    TEXT,
  metrics_json  TEXT,
  proposal_json TEXT,
  gate_json     TEXT,
  status        TEXT,             -- done | merged | rolled_back | rejected
  created_at    TEXT
);
"""


def _conn() -> sqlite3.Connection:
    DB.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute(_SCHEMA)
    return conn


def record(exp_id: str, kind: str, split: str, config_hash: str, git_commit: str,
           metrics: dict, parent_exp: str | None = None,
           proposal: dict | None = None, gate: dict | None = None,
           status: str = "done") -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (exp_id, parent_exp, kind, split, config_hash, git_commit,
             json.dumps(metrics, ensure_ascii=False),
             json.dumps(proposal, ensure_ascii=False) if proposal else None,
             json.dumps(gate, ensure_ascii=False) if gate else None,
             status, datetime.now(timezone.utc).isoformat()))


def set_status(exp_id: str, status: str) -> None:
    with _conn() as c:
        c.execute("UPDATE experiments SET status=? WHERE exp_id=?", (status, exp_id))


def latest(kind: str, split: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT exp_id, config_hash, metrics_json FROM experiments "
            "WHERE kind=? AND split=? ORDER BY created_at DESC LIMIT 1",
            (kind, split)).fetchone()
    if not row:
        return None
    return {"exp_id": row[0], "config_hash": row[1], "metrics": json.loads(row[2])}


def history(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT exp_id, kind, status, proposal_json, gate_json, metrics_json "
            "FROM experiments ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        out.append({"exp_id": r[0], "kind": r[1], "status": r[2],
                    "proposal": json.loads(r[3]) if r[3] else None,
                    "gate": json.loads(r[4]) if r[4] else None,
                    "metrics": json.loads(r[5]) if r[5] else None})
    return out
