# Contributing to HouseOfMath

Thank you for considering a contribution! HouseOfMath is community-curated and the most valuable contributions are usually new questions for the Question Bank.

## Setup

```bash
git clone https://github.com/batlabx/HouseOfMath
cd HouseOfMath
pip install -e ".[all]"   # install with every LLM extra
houseofmath init
```

## Adding questions

There are three supported paths, all of which require human review before content lands in the live bank.

### 1. Hand-author one question

```bash
houseofmath add
```

Walks you through every required field (`id`, `grade`, `question`, `options`, `correct`, `tags`, `explanation`, `source`, `license`), validates the result, and writes it to `Question Bank/<topic>/<level>.json`.

### 2. LLM-generate a batch

```bash
houseofmath generate --topic algebra --level medium --grade 7 --count 50
```

Output lands in `Question Bank/_pending/algebra/medium.json`. **Review every question** — LLMs hallucinate math constantly. When a question passes muster, promote it:

```bash
houseofmath promote alg-medium-042
```

### 3. Import a public dataset

Add a script under `scripts/importers/` that:

- Maps source content into the question schema
- Populates `source` and `license` fields
- Outputs to `_pending/` (importers never write to the live bank)
- Is idempotent — re-running doesn't duplicate IDs

Existing examples: `import_openstax.py`, `import_ck12.py`.

## Validating

Before opening a PR, every contributor must run:

```bash
houseofmath validate
```

This enforces:

- JSON schema compliance
- Unique IDs across the entire bank
- `options` has exactly 4 entries
- `correct` is in `[0, 3]`
- `grade` is `null` or in `[3, 9]`
- `explanation` is non-empty
- LaTeX in `question`, `options`, and `explanation` parses cleanly

CI runs the same check on every PR via GitHub Actions.

## PR checklist

- [ ] `houseofmath validate` passes locally
- [ ] `pytest` passes locally
- [ ] New questions cite a `source` and `license` (when imported)
- [ ] Sample IDs listed in the PR description for spot-checking
- [ ] No directly-written entries in `Question Bank/_pending/` (only `promote` writes to live)

## Code contributions

Pure code changes (CLI flags, new LLM adapters, UI improvements) follow the same flow:

1. Open an issue first describing the change
2. Implement with a test
3. `pytest` must pass
4. PR with a one-paragraph description

### Adding a new LLM adapter

A new provider is one file (~30 lines) implementing `houseofmath.llm.base.LLMClient`:

```python
class LLMClient(Protocol):
    def chat(self, messages: list[dict]) -> str: ...
    def is_available(self) -> bool: ...
```

Wire it into `houseofmath.llm.factory.get_client()` and the `houseofmath init` auto-detector.

## Code of conduct

Be kind. Assume good faith. Math is hard; reviewing math is harder. Reviewers and authors are both volunteering their time.
