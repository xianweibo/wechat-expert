"""????????????

- normalize_quotes:? LLM ???????? ASCII ??????????
  ? HTML entity,???? JSON ?????? mp_proxy ?? HTTP 400
  (SyntaxError: Expected ',' or '}' after property value in JSON at position 111)?
- write_draft:? dict ???????? JSON,?????????,
  ???? fail-fast ????? mp_proxy ????

????(???):
- ?? " ????(CJK ?? / ???? / ??? ASCII),??????? \u201C / \u201D
  (????,????????)?
- ??(????:HTML ??? style="..."),?? &quot; HTML entity,
  ?? JSON/HTML ????
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LDQ = "\u201C"
RDQ = "\u201D"


def _is_cjk_context(c: str) -> bool:
    if not c:
        return False
    code = ord(c)
    if code <= 0x7F:
        return False
    if 0x4E00 <= code <= 0x9FFF:
        return True
    if 0x3400 <= code <= 0x4DBF:
        return True
    if 0xF900 <= code <= 0xFAFF:
        return True
    if 0x3000 <= code <= 0x303F:
        return True
    if 0xFF00 <= code <= 0xFFEF:
        return True
    return True


def normalize_quotes(text: str) -> str:
    if not text:
        return text
    out = []
    open_quote = True
    chars = text
    for i, ch in enumerate(chars):
        if ch != '"':
            out.append(ch)
            continue
        prev_ch = chars[i - 1] if i > 0 else ""
        next_ch = chars[i + 1] if i + 1 < len(chars) else ""
        if _is_cjk_context(prev_ch) or _is_cjk_context(next_ch):
            out.append(LDQ if open_quote else RDQ)
            open_quote = not open_quote
        else:
            out.append("&quot;")
    return "".join(out)


def _normalize_deep(obj):
    if isinstance(obj, str):
        return normalize_quotes(obj)
    if isinstance(obj, dict):
        return {k: _normalize_deep(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_deep(v) for v in obj]
    return obj


def build_payload(draft: dict, ensure_ascii: bool = False) -> str:
    cleaned = _normalize_deep(draft)
    payload = json.dumps(cleaned, ensure_ascii=ensure_ascii)
    try:
        json.loads(payload)
    except json.JSONDecodeError as e:
        snippet = payload[max(0, e.pos - 40):e.pos + 40]
        sys.stderr.write(
            f"[draft_helpers] JSON ???? @ pos {e.pos}: {e.msg}\n"
            f"  snippet: {snippet!r}\n"
        )
        raise
    return payload


def write_draft(draft: dict, out_path, ensure_ascii: bool = False) -> int:
    payload = build_payload(draft, ensure_ascii=ensure_ascii)
    Path(out_path).write_text(payload, encoding="utf-8")
    return len(payload.encode("utf-8"))


if __name__ == "__main__":
    sample = {
        "title": 'SpaceX "???" 135 ??',
        "content": '<p>???"???"?????</p>',
        "nested": {"k": 'a "b" c "d"'},
    }
    out_path = Path(__file__).resolve().parent / "draft_helpers_selftest.json"
    n = write_draft(sample, out_path)
    print(f"selftest: wrote {n} bytes -> {out_path}")