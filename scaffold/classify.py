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
System_Prompt



