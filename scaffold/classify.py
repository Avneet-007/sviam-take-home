"""
Session integrity classifier — two-stage approach.
 
Stage 1: Deterministic pre-filter
    Catches cases where mechanical signals are unambiguous.
    Near-zero false positive risk. No LLM tokens spent.
 
Stage 2: LLM classifier (claude-sonnet-4-20250514)
    Handles ambiguous sessions using a pre-computed feature summary.
    Raw JSON is never sent — the LLM receives named, derived signals
    it can actually reason about rather than raw arrays.
 
Error asymmetry is baked into both stages: when evidence is mixed,
default to organic. A false accusation destroys a real person's
interview. A missed cheater is a hiring risk the company can recover from.
"""
 
import json
import os
import httpx
 
# STAGE 1 — DETERMINISTIC PRE-FILTER 
def _deterministic(session: dict) -> dict | None:
    """
    Return a classification if mechanical signals are conclusive,
    or None to fall through to the LLM.

    Rules here are essentially impossible for an honest candidate to trip.
    """
    events   = session["events"]
    code     = session["code"]
 
    pastes  = [e for e in events if e["type"] == "paste"]
    deletes = [e for e in events if e["type"] == "delete"]
    ks      = [e for e in events if e["type"] == "keystroke"]
    code_len = len(code)
 
    # Rule 1: Single paste covers ≥80% of final code, zero corrections
    # No innocent explanation: the candidate pasted almost all the solution
    # and never touched it.
    if len(pastes) == 1 and len(deletes) == 0 and len(ks) <= 3:
        paste_len = pastes[0].get("content_length", 0)
        if code_len > 0 and paste_len / code_len >= 0.80:
            return {
                "session_id": session["session_id"],
                "label":      "pasted",
                "confidence": "high",
                "reason": (
                    f"Single paste of {paste_len} chars covers "
                    f"{paste_len / code_len:.0%} of final code "
                    f"with zero corrections and {len(ks)} keystroke event(s)."
                ),
                "stage": "deterministic",
            }
 
    # Rule 2: All keystroke bursts sub-75ms with <20ms variance across 5+ bursts
    # Humans cannot physically sustain this uniformity — it is bot/autocomplete output.
    if len(ks) >= 5:
        speeds = [e.get("avg_ms_between_keys", 999) for e in ks
                  if e.get("avg_ms_between_keys", 0) > 0]
        if speeds and max(speeds) < 75 and (max(speeds) - min(speeds)) < 20:
            return {
                "session_id": session["session_id"],
                "label":      "ai_generated",
                "confidence": "high",
                "reason": (
                    f"Typing speed physically impossible for a human: "
                    f"max {max(speeds):.0f}ms/key across {len(speeds)} bursts, "
                    f"variance only {max(speeds) - min(speeds):.0f}ms."
                ),
                "stage": "deterministic",
            }
 
    return None
 
 
# ─────────────────────────────────────────────────────────────
# STAGE 2 — LLM CLASSIFIER
# ─────────────────────────────────────────────────────────────
System_Prompt= """You are an integrity detection engine for a technical interview platform.
Your job is to classify coding sessions as organic, pasted, or ai_generated.

CLASSIFICATION DEFINITIONS:
- organic: candidate typed the code themselves, with natural human variation
- pasted: candidate pasted code from an external source
- ai_generated: code was written by an AI tool and inserted verbatim or near-verbatim

SIGNAL ANALYSIS ranking by reliability:

1. PASTE EVENTS (strongest mechanical signal)
   - Single large paste covering most of the final code: pasted
   - Paste of a comment/docstring only, with code being typed after: organic
     (common pattern: candidate pasted API docs for reference)
   - Multiple small pastes scattered with corrections: less suspicious
   - Paste after a long pause (20-60s): possibility AI generation
   - Paste followed by zero corrections: points to strong cheating signal

2. TYPING SPEED VARIANCE (use variance, NOT absolute speed)
   - Organic: HIGH variance (50-150ms spread)
   - AI-generated: extremely LOW variance (<25ms spread), uniformly fast
   - A nervous fast typist averages 100ms/key but still shows >30ms variance
   - Variance <20ms across 5+ keystroke bursts = bot-like signal

3. DELETION / CORRECTION PATTERN
   - Organic: scattered deletions throughout: as humans make typos/ change their minds
   - AI-generated: zero or near-zero deletions:  as AI output is clean on first generation
   - Pasted: zero deletions after the paste event

4. SESSION TIMELINE
   - Organic: duration is proportional to the code length; pauses distributed throughout
   - AI-generated: short session; one long initial pause then fast sustained output
   - Pasted: very short for code volume; most time before/after paste

5. PAUSE PATTERN
   - Organic: many 10-45s pauses distributed throughout:  humans think between lines
   - AI-generated: very few short pauses (5-10s): AI doesn't need to think
   - Long pauses (>30s) DISTRIBUTED throughout:  strong organic signal

6. CODE STYLE
   - AI-generated: type annotations, full docstrings with Arguments/Returns/Examples sections,
     multiple implementations, comprehensive test suites:  over-engineered for interview
   - Pasted: clean idiomatic code; possible docstring if source had one
   - Organic: informal variable names, possibly messy, no docstrings

7. CODE-TO-TIME RATIO
   - Suspicious: >2.0 characters/sec with zero deletions
   - Not suspicious if paste events explain the ratio

BOUNDARY CASES:
- "Organic with paste": candidate pasted a comment or utility snippet, then typed the
  solution - classify this as organic if typing after paste shows corrections and pauses
- "Memorized solution": practiced candidate types fast and cleanly - classify this as organic if
  speed variance is human-like (>30ms) and there are distributed pauses
- "AI-then-edited": candidate used AI then edited heavily - this means low confidence, lean towards organic

ERROR ASYMMETRY:
Falsely accusing an honest candidate is MUCH more costly than missing a cheater.
- False positive: destroys their interview result, legal risks, damager of trust on platform
- False negative: cheater proceeds; some process later in the process may still catch them
Therefore:
- Mixed or ambiguous evidence: classify is as organic at low/medium confidence
- confidence=high only when MULTIPLE strong signals align consistently
- Never high confidence from a single signal alone"""

def _build_features(session: dict) -> str:
    """
    Pre-compute named signals before sending to the LLM.
 
    LLMs do arithmetic poorly on raw JSON arrays. Giving them labelled,
    pre-digested features with thresholds noted improves accuracy
    significantly — especially for the speed variance and deletion ratio.
    """
    events = session["events"]
    code = session["code"]
    duration = session["session_duration_seconds"]
 
    pastes  = [e for e in events if e["type"] == "paste"]
    deletes = [e for e in events if e["type"] == "delete"]
    ks = [e for e in events if e["type"] == "keystroke"]
    pauses = [e for e in events if e["type"] == "pause"]
    jumps = [e for e in events if e["type"] == "cursor_jump"]
 
    code_len = len(code)
 
    # Typing speed
    speeds  = [e["avg_ms_between_keys"] for e in ks if e.get("avg_ms_between_keys", 0) > 0]
    spd_avg = round(sum(speeds) / len(speeds), 1) if speeds else 0
    spd_var = round(max(speeds) - min(speeds), 1) if len(speeds) >= 2 else 0
 
    # Volume
    chars_typed   = sum(e.get("chars", 0) for e in ks)
    chars_pasted  = sum(e.get("content_length", 0) for e in pastes)
    chars_deleted = sum(e.get("chars_deleted", 0) for e in deletes)
    del_ratio     = round(chars_deleted / max(chars_typed, 1), 2)
    code_rate     = round(code_len / max(duration, 1), 2)
 
    # Pauses
    pause_secs  = [e.get("duration_seconds", 0) for e in pauses]
    long_pauses = [p for p in pause_secs if p >= 20]
 
    # Per-paste context: what was pasted, and what happened after?
    paste_ctx = []
    for pe in pastes:
        pt      = pe["timestamp"]
        pre     = [e for e in pauses if e["timestamp"] < pt and pt - e["timestamp"] < 90]
        pre_max = max((e["duration_seconds"] for e in pre), default=0)
        after_dels = sum(1 for e in deletes if e["timestamp"] > pt)
        paste_ctx.append({
            "at_t":round(pt, 1),
            "length":pe.get("content_length", 0),
            "preview":pe.get("content_preview", "")[:55],
            "pre_pause_s":round(pre_max, 1),
            "corrections_after": after_dels,
        })
 
    # Code style
    has_docstring = '"""' in code or "'''" in code
    has_type_hints = ("->" in code or ": int" in code or ": str" in code or "List[" in code or "list[" in code or "Optional" in code)
    has_args_section = "Args:" in code or "Parameters:" in code
    has_multi_impl = (code.count("def ") + code.count("function ")) >= 3
    has_test_suite = code.count("assert ") >= 3
 
    lines = [
        f"Session: {session['session_id']} | Problem: {session['problem_id']} | Language: {session['language']}",
        f"Duration: {duration}s ({round(duration / 60, 1)} min) | Code length: {code_len} chars",
        "",
        " PRODUCTION RATE ",
        f"  chars/sec: {code_rate}  [suspicious if >2.0 with zero deletions]",
        f"  chars typed: {chars_typed} | chars pasted: {chars_pasted} | chars deleted: {chars_deleted}",
        f"  deletion ratio: {del_ratio}  [low = suspicious for non-trivial code]",
        "",
        "── TYPING SPEED ──",
        f"  avg ms/key: {spd_avg}ms | variance (max−min): {spd_var}ms  [<20ms across 5+ bursts = bot-like]",
        f"  keystroke bursts: {len(ks)}",
        "",
        "── PASTE EVENTS ──",
        f"  count: {len(pastes)}",
    ]
    if paste_ctx:
        for p in paste_ctx:
            lines.append(
                f"  • t={p['at_t']}s | length={p['length']}c"
                f" | pre-pause={p['pre_pause_s']}s"
                f" | corrections-after={p['corrections_after']}"
            )
            lines.append(f"    preview: {p['preview']!r}")
    else:
        lines.append("  (none)")
 
    lines += [
        "",
        "── PAUSE PATTERN ──",
        f"  total: {len(pauses)} | long (≥20 s): {len(long_pauses)}",
        f"  durations: {[round(p, 1) for p in pause_secs]}",
        "",
        "── CORRECTIONS ──",
        f"  delete events: {len(deletes)} | cursor jumps: {len(jumps)}",
        "",
        "── CODE STYLE ──",
        f"  has docstring:{has_docstring}",
        f"  has type annotations:{has_type_hints}",
        f"  has Args/Returns section: {has_args_section}",
        f"  has 3+ function defs:{has_multi_impl}",
        f"  has 3+ assert statements:{has_test_suite}",
        "",
        "── FINAL CODE ──",
        "```",
        code,
        "```",
        "",
        "Classify this session. Respond with JSON only.",
    ]
    return "\n".join(lines)
 
 
def _llm_classify(session: dict) -> dict:
    """Call the Anthropic API and return the parsed classification."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
 
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 200,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": _build_features(session)}],
    }
    headers = {
        "Content-Type":      "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key":         api_key,
    }
 
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
 
        # Extract text from response
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block["text"]
 
        # Strip accidental markdown fences
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text  = parts[1] if len(parts) > 1 else parts[0]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
 
        result = json.loads(text)
        result["session_id"] = session["session_id"]
        result["stage"]      = "llm"
        return result
 
    except Exception as exc:
        # On any error, default to organic/low — never silently accuse anyone
        return {
            "session_id": session["session_id"],
            "label":      "organic",
            "confidence": "low",
            "reason":     f"[classifier error — defaulting to organic]: {exc}",
            "stage":      "error",
        }


def classify_session(session: dict) -> dict:
    """
    Classify a coding session as organic / pasted / ai_generated.
 
    Args:
        session: A session dict with keys: session_id, problem_id, language,
                 session_duration_seconds, code, events
 
    Returns:
        {
            "session_id": "session_01",
            "label": "organic" | "pasted" | "ai_generated",
            "confidence": "low" | "medium" | "high",
            "reason": "One-line explanation of why this classification.",
            "stage": "deterministic" | "llm" | "error",
        }
    """
    # TODO: Build your prompt from the session data.   ← handled in _build_features()
    # TODO: Call your LLM (OpenAI, Anthropic, etc.)    ← handled in _llm_classify()
    # TODO: Parse the response into expected format.   ← handled in _llm_classify()
 
    # Stage 1: deterministic rules (no LLM, near-zero false positive risk)
    det = _deterministic(session)
    if det is not None:
        return det
 
    # Stage 2: LLM for everything ambiguous
    return _llm_classify(session)



