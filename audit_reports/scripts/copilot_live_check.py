"""Live check of the Shariah Policy Copilot through Django (needs the backend on :8000, the copilot on :8001 and the demo seed).
Run: python audit_reports/scripts/copilot_live_check.py   (exit 0 = all checks passed)
It asks one question and verifies the answer carries citations, that a question with no evidence gets the fixed fallback
instead of an invented answer, and that an investor cannot reach the copilot at all.
"""
import json
import sys
import urllib.request

BASE = "http://localhost:8000/api/v1/"
FAILED = []


def call(path, token=None, body=None, tenant="NOVU-DEMO"):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "X-Tenant-Code": tenant}, method="POST" if body is not None else "GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, None


def login(email):
    return call("auth/login/", body={"email": email, "password": "Amanah@2026!"})[1]["access"]


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILED.append(name)


board = login("board@novulabsdemo.test")
status, docs = call("ai/shariah-copilot/documents/", board)
check("the copilot lists its approved documents", status == 200 and len(docs) > 0, f"HTTP {status}")

status, answer = call("ai/shariah-copilot/ask/", board, {"question": "What is the policy on late payment charges?"})
text = (answer or {}).get("research_summary", "")
check("an answer with evidence cites its sources", status == 200 and "[" in text and "Section" in text, f"HTTP {status}")
check("the answer is recorded as an AI recommendation (BR-009)", bool((answer or {}).get("recommendation_id") or (answer or {}).get("id")))

status, nothing = call("ai/shariah-copilot/ask/", board, {"question": "What is the capital of Atlantis and its football results?"})
summary = (nothing or {}).get("research_summary", "")
check("a question with no evidence gets the fixed fallback, not an invention", status == 200 and "No approved internal Shariah ruling" in summary, summary[:80])

status, _ = call("ai/shariah-copilot/ask/", login("investor@novulabsdemo.test"), {"question": "x"})
check("an investor cannot use the copilot", status in (401, 403), f"HTTP {status}")
sys.exit(1 if FAILED else 0)
