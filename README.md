# SVIAM | AI Engineering Intern Take Home Assignment

## Context

SVIAM builds an AI interviewer that conducts live technical interviews and scores candidates in real time. A critical piece of the product is **integrity detection**: figuring out whether a candidate solved the problem themselves, pasted code from somewhere, or had an AI write it for them. Getting this wrong in either direction is expensive. Flag an honest candidate and you destroy trust in the product. Miss a cheater and you undermine the entire assessment. This assignment puts you in the middle of that problem.

## The Rules

**You may and should use AI tools.** Claude, GPT, Copilot, whatever you prefer. We are not testing whether you can write code. AI handles that. We are testing three things:

1. **Your prompt design.** Can you get an LLM to reason well about messy, ambiguous data?
2. **Your evaluation methodology.** Can you measure whether your approach actually works, and do you understand what "works" means in a hiring context?
3. **Your failure analysis.** Can you identify where the approach breaks and what you would do differently?

A mediocre prompt with a sharp evaluation harness and honest failure analysis beats a clever prompt with no evaluation.

## Time Expectation

Aim for **4 to 6 hours**. A clean partial solution beats a sprawling complete one. If you only get through Part 1 and half of Part 2, that is completely fine. Just make what you submit polished.

## Assumptions

The spec is intentionally underspecified in places. If you make an assumption, write it down in `SUBMISSION.md`. We read the assumptions list closely. Good assumptions demonstrate product thinking. Bad assumptions demonstrate skimming.

---

## The Dataset

`/data/sessions/` contains **18 synthetic coding session files** (`session_01.json` through `session_18.json`). Each file represents one candidate solving a short coding problem.

`/data/labels.json` contains ground truth labels for **only 5** of the 18 sessions. The other 13 are unlabeled. This is intentional. In production, you rarely have a complete answer key.

### Session JSON Schema

```json
{
  "session_id": "session_01",
  "problem_id": "two_sum",
  "language": "python",
  "session_duration_seconds": 1380,
  "code": "def two_sum(nums, target):\n    ...",
  "events": [
    {
      "type": "keystroke",
      "timestamp": 2.1,
      "text": "def ",
      "chars": 4,
      "avg_ms_between_keys": 145
    },
    {
      "type": "delete",
      "timestamp": 18.3,
      "chars_deleted": 5
    },
    {
      "type": "paste",
      "timestamp": 45.0,
      "content_length": 128,
      "content_preview": "import collections..."
    },
    {
      "type": "cursor_jump",
      "timestamp": 50.0,
      "from_line": 1,
      "to_line": 15
    },
    {
      "type": "pause",
      "timestamp": 60.0,
      "duration_seconds": 12.5
    }
  ]
}
```

**Event Types:**

| Type | Fields | Description |
|------|--------|-------------|
| `keystroke` | `text`, `chars`, `avg_ms_between_keys` | A burst of typing. `avg_ms_between_keys` is the mean inter key delay in milliseconds within this burst. |
| `delete` | `chars_deleted` | Backspace or deletion event. |
| `paste` | `content_length`, `content_preview` | A paste from clipboard. `content_preview` shows the first ~50 characters. |
| `cursor_jump` | `from_line`, `to_line` | Cursor moved non sequentially (jumped to a different section). |
| `pause` | `duration_seconds` | A gap in activity. Only pauses greater than 5 seconds are recorded. |

All events have a `timestamp` (seconds from session start) and `type`.

---

## The Assignment

### Part 1: Build (Prompt Design)

Write a prompt that takes a session JSON file and classifies it as one of:

- `organic` : the candidate wrote the code themselves
- `pasted` : the candidate pasted code from an external source
- `ai_generated` : the code was written by an AI tool

The output should include:
- The classification label
- A confidence level: `low`, `medium`, or `high`
- A one line reason

You can use any LLM (GPT 4, Claude, Gemini, open source models, your choice). Iterate on the prompt until you are satisfied. The final prompt goes in `SUBMISSION.md`.

**Hint:** Think about what signals in the event log actually distinguish these categories. Typing speed variance matters more than typing speed. What does a paste event followed by zero corrections tell you? What does a 45 second pause before a clean burst of code mean?

### Part 2: Evaluate (The Real Test)

Build a small evaluation harness that:

1. Runs your prompt across all 18 sessions
2. Compares the results against the 5 labeled sessions
3. Reports metrics

You must **choose your own metrics**. "Overall accuracy" is one number you might report, but ask yourself: in a product that decides whether to flag a real human's interview, are all errors equal? What kind of mistake is more expensive? Your metric choices tell us more about your product instincts than your code does.

Put the harness in `/scaffold/` or a new directory, your call. It should be runnable with a single command (document how in `SUBMISSION.md`).

### Part 3: Failure Analysis (Judgment)

Write 300 to 600 words in `SUBMISSION.md` answering:

- Where does the LLM based approach break? Which sessions did it get wrong, and why?
- Where would you **not** trust this system to make a decision autonomously?
- Which of these checks should be **deterministic code** instead of an LLM call? Why?
- Where is the model **confidently wrong** (high confidence, wrong label)?
- What would you build differently with 10,000 real sessions instead of 18 synthetic ones?

---

## How to Submit

1. **Fork** this repo
2. Do your work on a branch (or main, your call)
3. Fill in `SUBMISSION.md`
4. Push your fork and share the link with us

Include all code, the filled in submission, and any notes. Do not submit compiled or built artifacts.

---

## How We Evaluate

We are looking for the following, in rough priority order:

1. **Independent discovery of error asymmetry.** Do you figure out, on your own, that falsely accusing an honest candidate is far worse than missing a cheater? We do not spell this out. If you find it, it tells us you think about the product, not just the model.
2. **Real evaluation metrics.** Not vibes, not "it seems to work." Numbers, with reasoning about what the numbers mean.
3. **Epistemic honesty.** Do you know where your approach fails? Do you say so clearly? Bonus if you identify failure modes we had not thought of.
4. **Prompt quality.** Is the prompt specific, well structured, and does it leverage the right signals from the event data?
5. **Quality of assumptions.** What did you assume, and do the assumptions show product thinking or shortcuts?
6. **Process log.** Your `SUBMISSION.md` includes a short paragraph about what you tried, what the AI got wrong on the first pass, and how you caught and corrected it. This tells us whether you were driving the AI or along for the ride.

What we do not care about: fancy code, complex abstractions, perfect coverage. We want clear thinking over clever engineering.

---

## Setup

```bash
# Clone your fork
git clone <your fork url>
cd sviam-take-home

# Python
pip install -r scaffold/requirements.txt

# Or Node.js / TypeScript
cd scaffold && npm install
```

The scaffold provides minimal starter code in both Python and JavaScript. Pick whichever you prefer. You are also free to ignore the scaffold entirely and start from scratch.

---

Good luck. We would rather see you be right about something small than wrong about something big.
