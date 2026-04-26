# Question Bank

The HouseOfMath Question Bank — version-controlled, schema-validated multiple-choice math questions for grades 3 through 9.

## Layout

```
Question Bank/
├── README.md                  ← this file
├── algebra/
│   ├── easy.json
│   ├── medium.json
│   └── difficult.json
├── arithmetic/
├── fractions/
├── geometry/
├── percentages/
└── _pending/                  ← LLM-generated drafts awaiting human review
```

Each `<topic>/<level>.json` file is a JSON array of question objects. The Curator subagent reads these directly at runtime; nothing else.

## Question schema

```json
{
  "id": "alg-medium-001",
  "grade": 7,
  "question": "Solve: $3x + 4 = 19$.",
  "options": ["$x = 4$", "$x = 5$", "$x = 6$", "$x = 7$"],
  "correct": 1,
  "tags": ["linear-equations", "two-step"],
  "explanation": "Subtract 4: $3x = 15$. Divide by 3: $x = 5$.",
  "source": "houseofmath-seed-v1",
  "license": "MIT"
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | string | Unique across the entire bank. Format: `<topic-prefix>-<level>-<3-digit-seq>`. |
| `grade` | int 3–9 or null | `null` means grade-agnostic. |
| `question` | string | Markdown with LaTeX (`$...$` inline, `$$...$$` block). |
| `options` | array of 4 strings | Exactly 4 entries, also Markdown+LaTeX. |
| `correct` | int 0–3 | Index into `options`. |
| `tags` | array of strings | Sub-skill tags, lowercase-hyphenated. Used by the Reporter for weak-area analysis. |
| `explanation` | string | Required. Static so the tool works offline. |
| `source` | string | Provenance — `houseofmath-seed-v1`, `openstax-prealgebra-ch3`, contributor handle, etc. |
| `license` | string | License of the question content. |

Topic ID prefixes: `alg` algebra, `ari` arithmetic, `frac` fractions, `geo` geometry, `pct` percentages.

## What's in the bank right now (seed v1)

- **150 questions total**, 10 per topic × level
- **5 topics**: arithmetic, fractions, percentages, algebra, geometry
- **3 levels** per topic: easy, medium, difficult
- **Grade distribution**: grade 3 (13 q), grade 4 (16), grade 5 (25), grade 6 (28), grade 7 (28), grade 8 (23), grade 9 (17)
- **All original content**, MIT-licensed, hand-authored from standard grade 3–9 curricula
- All entries pass `houseofmath validate`

The bank is intentionally small at v1 — a quality seed that demonstrates the schema and gives the UI something to test against. Contributors expand from here.

## How to add questions

Three supported paths, in order of how often they should be used:

### 1. `houseofmath generate` (LLM-drafted, recommended for bulk)
```bash
houseofmath generate --topic algebra --level medium --grade 7 --count 50
```
Generates candidates into `_pending/algebra/medium.json`. **Review every one** — the LLM is a drafter, not the author of record. Once a question is reviewed and edited:
```bash
houseofmath promote alg-medium-051
```
moves it into the live bank.

### 2. `houseofmath add` (interactive, one at a time)
```bash
houseofmath add
```
Walks through every required field, runs validation, writes directly to the appropriate file. Best for quick fixes or single high-quality additions.

### 3. Public dataset importers (P1)
Scripts under `scripts/importers/` (e.g., `import_openstax.py`, `import_ck12.py`) populate `_pending/` from openly-licensed sources. Same review-then-promote flow applies. **Importers are not in the v1 seed** — they're a P1 contribution opportunity.

## Validation

`houseofmath validate` runs in CI and must pass before any PR merges. It checks:

- JSON parses cleanly
- Every record has all required fields
- IDs are unique across the whole bank
- `options` has exactly 4 entries
- `correct` is in `[0, 3]`
- `grade` is `null` or in `[3, 9]`
- `explanation` is non-empty
- LaTeX in `question`, `options`, and `explanation` parses without errors

## Licensing notes

The seed bank is MIT-licensed original content. **Imported questions retain their source license** (e.g., `CC-BY-4.0` from OpenStax). Always populate the `source` and `license` fields accurately — `houseofmath validate` enforces presence for imported sections, and downstream redistribution depends on them.

If you contribute a question and it's based on a textbook problem, **rewrite it in your own words** and credit the textbook in `source`. Don't copy verbatim.

## Quality bar

Before opening a PR, every new question should:

1. **Be mathematically correct** — verify the answer twice
2. **Be grade-appropriate** — match the `grade` tag's expected curriculum
3. **Have plausible distractors** — wrong options should reflect common mistakes (e.g., off-by-one, sign errors, applying the wrong operation), not random numbers
4. **Have a clear explanation** — the explanation should teach the concept, not just restate the answer
5. **Pass `houseofmath validate`** locally
