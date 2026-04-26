# HouseOfMath — Question Generation Prompt

You are generating multiple-choice math practice questions for **grades 3 through 9**. Output a JSON array of question objects matching this schema exactly:

```json
{
  "id": "<topic-prefix>-<level>-<seq>",
  "grade": 3-9 or null,
  "question": "Markdown with LaTeX, $...$ inline or $$...$$ block",
  "options": ["string", "string", "string", "string"],
  "correct": 0-3,
  "tags": ["lowercase-hyphenated", "sub-skill-tag"],
  "explanation": "Step-by-step worked solution. Required.",
  "source": "string identifying you as the source (e.g. 'llm-generated-claude')",
  "license": "MIT"
}
```

## Hard rules

- Exactly **4 options** per question. No more, no fewer.
- `correct` is the **integer index** (0, 1, 2, or 3) of the correct option.
- `explanation` is **required and non-empty** — this is what the student reads when reviewing. Make it pedagogically useful.
- `id` must be unique. Use the prefix matching the topic:
  - algebra → `alg`
  - arithmetic → `arith`
  - geometry → `geo`
  - fractions → `frac`
  - percentages → `pct`
- `tags` are lowercase, hyphen-separated, no spaces (e.g. `linear-equations`, `area-of-triangle`).
- `grade` is the integer grade for which the question is calibrated, or `null` if grade-agnostic.
- All math must be wrapped in LaTeX delimiters.

## Calibration guidance

| Level | What "level" means |
|---|---|
| `easy` | One step. The operation is named or obvious. A grade-appropriate student should solve it in under a minute. |
| `medium` | Two or three steps. Requires combining skills (e.g., distribute then collect like terms). |
| `difficult` | Multi-step, multiple sub-skills, or a small twist (negative numbers, reversed wording, edge cases). Still solvable by a strong student in the target grade. |

## Quality bar

- Every option must be **plausible** — distractors should reflect common mistakes, not random numbers.
- The correct answer must be **objectively correct** — verify your arithmetic.
- Avoid trick questions. Avoid culturally specific contexts.
- Vary the question phrasing — don't repeat the same template ten times.

## Output rules

- Return **only** the JSON array. No prose, no markdown fences, no commentary.
- Make the JSON parseable on first try. If you're not sure of a value, omit the question rather than guess.
