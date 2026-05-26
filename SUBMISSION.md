# Submission | Avneet Kaur Sandhu

## Part 1: Prompt

Paste your final prompt below. If you iterated through multiple versions, you can briefly note what changed between the key iterations, but we mainly want the final version.

```
You are an integrity detection engine for a technical interview platform.
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
- Never high confidence from a single signal alone

FORMAT FOR THE OUTPUT- JSON only, no markdown:
{
  "label": "organic"/ "pasted"/ "ai_generated",
  "confidence": "low" / "medium"/ "high",
  "reason": "One sentence citing the primary signals."
}

```

### Prompt Design Notes

_Why did you structure the prompt this way? What signals does it focus on? What did you try that did not work?_

What I focused majorly on was the hint given "typing speed variance matters more than typing speed". A fast typist may average 90ms/key. BUt will show as natural arounnd 50 ms could be fast when typing and alow when thinking. Absoute speed would be a weak signal and variance would help to discriminate better. 
The first draft just sent the raw JSON file into the LLM and asked it to classify. This resulted in the ignorance of the event data. Also session 6 of being AI generated. Then I added the paste content preview feature which fixed this problem 

I added a deterministic pre-filter before the LLM call. Three rules fire before any API call:

Single paste >=80% of code + zero deletions:  pasted, high confidence
All keystroke bursts under 75ms with variance <20ms:  ai_generated, high confidence

---

## Part 2: Evaluation

### How to Run

```bash
# Install dependencies
pip install -r scaffold/requirements.txt

# Run full evaluation (18 sessions, metrics on 5 labeled)
ANTHROPIC_API_KEY=sk-ant-... python scaffold/evaluate.py
```

### Metrics

_What metrics did you choose and why? Report the numbers._

| Metric | Value |
|--------|-------|
| False Accusation rate| 0% |
| Cheat Detection rate | 100% |
| Overall accuracy | 100% |
| High Confidence Errors | 0 |

### Results Table

| Session | Predicted Label | Confidence | Reason | Ground Truth (if available) |
|---------|-----------------|------------|--------|-----------------------------|
| session_01 | organic | high | 8 distributed pauses, 5 deletions, speed variance 75ms — clear human typing pattern | organic |
| session_02 | ai_generated | high | Avg 62ms/key, variance only 17ms across 20 bursts — physically impossible for a human |  |
| session_03 | pasted | high | Single 285-char paste covers 84% of final code; zero deletions after paste | pasted |
| session_04 | ai_generated | high | Avg 105ms, variance 14ms, zero deletions, 4 short pauses — bot-like uniform output | |
| session_05 | organic | high | 8 deletions, 7 pauses up to 22s, speed variance 47ms — natural human rhythm | |
| session_06 | organic | medium | Paste was JSDoc comment only; function body typed over 700s with corrections and pauses | oprganic |
| session_07 | pasted | high | 3 paste events, zero deletions, only 2 keystroke events in a 240s session | |
| session_08 | organic | low | 1 deletion and distributed pauses suggest organic; narrow variance 13ms is the one concern | |
| session_09 | organic | high | 13 pauses including 25-45s blocks, 7 deletions, variance 57ms — strong human signal | |
| session_10 | ai_generated | high | Variance 15ms, zero deletions, full docstring with Args/Returns/Examples, 2.55 chars/sec | ai_generated |
| session_11 | organic | medium | Long 32-60s pauses distributed throughout; pacing consistent with difficult problem-solving | |
| session_12 | pasted | high | Single 248-char paste covers 82% of code; zero deletions, only 2 keystrokes | |
| session_13 | organic | high | Variance 105ms (highest in dataset), 55s thinking pause — unmistakably human | |
| session_14 | organic | low |Human pauses and 1 deletion suggest organic; narrow variance 23ms across 48 bursts is ambiguous  | | 
| session_15 | organic |high |Avg 268ms/key, 9 pauses, 0.29 chars/sec over 27 minutes — slow deliberate human pace | organic |
| session_16 | ai_generated |high | Avg 102ms, variance 18ms, zero deletions, 2.1 chars/sec — same signature as session_10 | |
| session_17 | pasted |medium | 3 paste events, 15 keystrokes, 2 deletions — medium not high because corrections exist | |
| session_18 | organic |low |5 pastes but 32 keystrokes and 1 deletion suggest own snippets; boundary case | |

---

## Part 3: Failure Analysis

_300 to 600 words. Where does the LLM break? Where would you not trust it? What should be deterministic code? Where is the model confidently wrong? What changes with 10k real sessions?_

The hardest failure mode is the memorized solution. A candidate who has practiced two_sum fifty times will type it in two minutes, with few pauses and almost no deletions. That session appears almost the same as a paste followed by a small fix. No classifier based only on behavioral signals can tell the difference between "I practiced this problem" and "I found this online this morning." Session_08 is a mild case; with a speed difference of 13ms and only one deletion, it is borderline, so I returned organic, low confidence instead of making a clear decision. 

The second difficult case is when a candidate edits AI-generated code. They ask ChatGPT for help, receive the code, and then spend ten minutes testing and tweaking it. After enough revisions, the session has deletions, cursor movements, and scattered pauses that mimic organic behavior. This requires detecting to code to known similar outputs. 

The second difficult case is when a candidate edits AI-generated code. They ask ChatGPT for help, receive the code, and then spend ten minutes testing and tweaking it. After enough revisions, the session has deletions, cursor movements, and scattered pauses that mimic organic behavior.The solution was to include the paste content preview in the feature summary, allowing the model to see that the paste started with /**, not with function code.

Any session where confidence != high should go to a human review queue, not be auto-acted on. Specifically: sessions where a paste appears early but subsequent keystrokes show substantial corrections; very short problems where organic typing genuinely produces 2+ chars/sec; non-native English speakers who type slowly but uniformly (legitimate human pattern that looks AI-like on variance metrics).

---

## Assumptions

_List every assumption you made. Example: "I assumed typing speed variance is more informative than absolute typing speed because..."_

1. The inclusion of memorised solutions in organic. 
2. Assumption that the key logger accuratly captures the Ctrl+V from fast typing
3. content_length in paste events estimates the actual pasted code size
4. Speed variance is computed per-session as max − min of burst averages

---

## Process Log

_One paragraph: what did you try, what did the AI get wrong on the first pass, how did you catch it and fix it? This tells us whether you were driving or riding._

My first approach sent the raw session JSON directly to Claude and asked it to classify. The model ignored most of the event data and instead focused on code style. It labeled session_06 as ai_generated because the code had a JSDoc comment and type annotations.
I saw that the paste event included only the comment template, not the function body. To fix this, I computed features before the API call.
The second important change was restructuring the speed guidance. I led with variance instead of absolute speed. The first draft of the prompt said "< 100ms = suspicious," which would have flagged session_09 as clean. Session_09 was a slow, thoughtful organic session that still had some bursts at 140ms. 
I added the deterministic pre-filter last to manage the obvious mechanical cases without LLM involvement.
