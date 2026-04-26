# HouseOfMath — Build Instructions (P0)

> An open-source, BYO-LLM math practice agent. Pick a topic, level, and grade — get a 10-question MCQ practice test in your browser. Works offline by default. Connect via your existing **Claude subscription** (through Claude Code), free-tier API keys, paid APIs, or a fully local model — your choice.

---

## 1. What HouseOfMath Is

HouseOfMath is a Python CLI tool that runs a local Streamlit app delivering multiple-choice math practice tests for **grades 3 through 9**. Questions live in a version-controlled `Question Bank/` folder inside the repo. The LLM is **optional** — the core practice loop works fully offline using static hints and explanations that ship with each question. Connecting an LLM (Claude, OpenAI, local Ollama, etc.) unlocks personalized post-test feedback and a richer Reporter summary.

**Inputs**
- `topic` — e.g., `algebra`, `geometry`, `arithmetic`, `fractions`, `percentages`
- `level` — `easy`, `medium`, or `difficult`
- `grade` — optional integer 3–9; filters the question pool further

**Output**
- A 10-question MCQ session in the browser
- Review mode after submission (every question with user answer, correct answer, full explanation)
- Score logged to local SQLite for progress tracking

**Non-goals for P0**
- Adaptive difficulty
- Multi-user accounts / hosted version
- Spaced repetition
- Free-response (non-MCQ) questions
- Timed tests
- Mobile app
- In-test hints

---

## 2. Quickstart (target end-user experience)

```bash
git clone https://github.com/<user>/houseofmath
cd houseofmath
pip install -e .
houseofmath init        # picks LLM provider, defaults to "none"
houseofmath run         # interactive prompts for topic + level + grade
```

Non-interactive form:

```bash
houseofmath run --topic algebra --level medium --grade 7
```

---

## 3. Architecture

```
┌──────────────┐      ┌────────────────┐      ┌──────────────────┐
│  CLI (Click) │─────▶│   Curator      │─────▶│  Streamlit App   │
│              │      │ (deterministic │      │   (browser UI)   │
└──────────────┘      │  question pick)│      └────────┬─────────┘
                      └────────────────┘               │
                                                       ▼
                                            ┌──────────────────┐
                                            │  Tutor (LLM)     │
                                            │  Reporter (LLM)  │
                                            │  optional        │
                                            └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │ ~/.houseofmath/  │
                                            │   history.db     │
                                            └──────────────────┘
```

Three subagents, one CLI, one Streamlit frontend, one SQLite store.

---

## 4. Subagents

### 4.1 Curator (no LLM)
Selects questions from the Question Bank.
- Reads `Question Bank/<topic>/<level>.json`
- Optionally filters by `grade` field
- Samples N questions (default 10), shuffles option order
- Returns a structured `QuestionSet` object to the Streamlit app
- Pure Python, no network, no LLM

### 4.2 Tutor (LLM, optional)
Activated only post-submission for the Review screen.
- Uses the static `explanation` shipped with each question by default
- If LLM is connected, can rephrase the explanation in simpler/different wording on user request ("Explain it differently")
- Falls back gracefully when `provider: none`

### 4.3 Reporter (LLM, optional)
Generates the end-of-test summary.
- Always shows: score, time taken, breakdown by sub-skill tag
- If LLM connected: writes a personalized paragraph identifying weak areas and suggested next topics, drawing on `history.db`
- If `provider: none`: shows a templated summary (still useful, just not personalized prose)

> **Why MCQ grading isn't a subagent:** for multiple choice it's just `user_answer == correct_index`. Lives inline in the Streamlit app.

---

## 5. Repository Structure

```
houseofmath/
├── README.md
├── LICENSE                          # MIT
├── CONTRIBUTING.md
├── instructions.md                  # this file
├── pyproject.toml                   # entry point: houseofmath = houseofmath.cli:main
├── houseofmath.config.example.yaml
├── houseofmath/
│   ├── __init__.py
│   ├── cli.py                       # Click commands
│   ├── curator.py                   # question selection
│   ├── tutor.py                     # LLM-powered explanation rephrasing
│   ├── reporter.py                  # end-of-test summary
│   ├── llm/
│   │   ├── base.py                  # LLMClient interface
│   │   ├── claude_code_client.py    # subscription auth via Claude Code CLI
│   │   ├── anthropic_client.py      # Anthropic API key
│   │   ├── openai_client.py         # OpenAI API key
│   │   ├── gemini_client.py         # Google AI Studio (free tier)
│   │   ├── ollama_client.py         # local LLM
│   │   └── none_client.py           # no-op for offline mode
│   ├── app/
│   │   └── streamlit_app.py         # the entire frontend
│   ├── storage/
│   │   └── history.py               # SQLite wrapper
│   └── validation/
│       └── schema.py                # JSON schema for Question Bank entries
├── Question Bank/
│   ├── algebra/
│   │   ├── easy.json
│   │   ├── medium.json
│   │   └── difficult.json
│   ├── arithmetic/
│   ├── geometry/
│   ├── fractions/
│   ├── percentages/
│   └── _pending/                    # LLM-generated, awaiting human review
├── scripts/
│   └── importers/
│       ├── import_openstax.py
│       └── import_ck12.py
└── tests/
    ├── test_curator.py
    ├── test_validation.py
    └── fixtures/
```

---

## 6. Question Bank Format

Each topic/level pair is a JSON file containing a list of question objects. **Schema is enforced by `houseofmath validate`.**

```json
[
  {
    "id": "alg-easy-001",
    "grade": 6,
    "question": "Solve for $x$: $2x + 6 = 14$",
    "options": [
      "$x = 2$",
      "$x = 4$",
      "$x = 6$",
      "$x = 8$"
    ],
    "correct": 1,
    "tags": ["linear-equations", "one-variable"],
    "explanation": "Subtract 6 from both sides: $2x = 8$. Divide by 2: $x = 4$.",
    "source": "openstax-prealgebra-ch3",
    "license": "CC-BY-4.0"
  }
]
```

**Field rules**
- `id` — unique across the entire bank, format `<topic-prefix>-<level>-<seq>`
- `grade` — integer 3–9, or `null` if grade-agnostic
- `question`, `options`, `explanation` — Markdown with LaTeX (`$...$` inline, `$$...$$` block)
- `options` — exactly 4 items
- `correct` — integer index 0–3 into `options`
- `tags` — array of sub-skill tags (used by Reporter for weak-area analysis); free-form but lowercase-hyphenated
- `explanation` — required, ships static so the tool works offline
- `source`, `license` — required when imported from a public dataset; nullable for original contributions

---

## 7. LLM Configuration (BYO-LLM)

HouseOfMath supports six provider options so users can connect using whatever they already have — a Claude subscription, a free API key, a paid API, a local model, or nothing at all.

### 7.1 The honest landscape

| Option | Cost | Account needed | Notes |
|---|---|---|---|
| `none` | Free | None | Fully offline. Static explanations only. **Default.** |
| `claude-code` | Covered by **Claude Pro/Max subscription** | Anthropic account + Claude Code installed | Recommended for Claude subscribers. No separate API key. |
| `gemini` | **Free tier** (15 req/min, 1M tokens/day) | Google account | No credit card required. Best zero-cost LLM option. |
| `ollama` | Free | None | Runs locally. Requires Ollama installed + a model pulled. |
| `anthropic` | Pay-per-use API | Anthropic API key with billing | Separate from Claude Pro subscription. |
| `openai` | Pay-per-use API | OpenAI API key with billing | **Note:** ChatGPT Plus/Pro subscriptions do NOT grant API access — these are separate products. |

**Not supported (and why):** ChatGPT Plus, Gemini Advanced (subscription tier), GitHub Copilot, Cursor, and similar consumer subscriptions do not expose programmatic access. There is no honest, ToS-compliant way to use them from a CLI tool. Users with these subscriptions should pick `gemini` (free tier), `claude-code` (if they also have a Claude subscription), or `ollama`.

### 7.2 Config file

Single config file at repo root: `houseofmath.config.yaml` (gitignored — contributors copy from `.example.yaml`).

```yaml
provider: none      # one of: none | claude-code | gemini | ollama | anthropic | openai

# Only the relevant block is read based on provider:

claude-code:
  # Uses the `claude` CLI from Claude Code, which carries the user's
  # subscription auth. No API key needed here.
  # Run `claude /login` once before first use.
  binary: claude              # path or name of the Claude Code CLI
  model: claude-sonnet-4-6    # optional; passes --model to the CLI

gemini:
  model: gemini-2.0-flash
  api_key_env: GOOGLE_AI_API_KEY   # get a free key at https://aistudio.google.com

ollama:
  base_url: http://localhost:11434
  model: llama3

anthropic:
  model: claude-sonnet-4-6
  api_key_env: ANTHROPIC_API_KEY

openai:
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
```

**Default is `provider: none`**, so the repo works zero-config out of the box. Users opt into LLM features explicitly via `houseofmath init`.

### 7.3 Adapter contract

`houseofmath/llm/base.py`:

```python
class LLMClient(Protocol):
    def chat(self, messages: list[dict]) -> str: ...
    def is_available(self) -> bool: ...
```

Adding a new provider is one file (~30 lines) implementing this protocol.

### 7.4 The `claude-code` adapter (subscription path)

The Claude Pro/Max subscription path works by shelling out to the user's already-authenticated Claude Code CLI:

```python
import shutil, subprocess

class ClaudeCodeClient:
    def __init__(self, binary: str = "claude", model: str | None = None):
        self.binary = binary
        self.model = model

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def chat(self, messages: list[dict]) -> str:
        prompt = "\n\n".join(m["content"] for m in messages)
        cmd = [self.binary, "-p", prompt]
        if self.model:
            cmd.extend(["--model", self.model])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        result.check_returncode()
        return result.stdout.strip()
```

The user runs `claude /login` once (handled by Claude Code itself) and the subscription auth is persisted. HouseOfMath never sees or stores the user's credentials.

### 7.5 Auto-detection in `houseofmath init`

`init` probes the environment in this order and recommends the highest-value option available:
1. Is `claude` on PATH and authenticated? → suggest `claude-code`
2. Is `ollama` running locally? → suggest `ollama`
3. Is `GOOGLE_AI_API_KEY` set? → suggest `gemini`
4. Is `ANTHROPIC_API_KEY` set? → suggest `anthropic`
5. Is `OPENAI_API_KEY` set? → suggest `openai`
6. Otherwise → suggest `none` and explain how to upgrade later.

---

## 8. CLI Commands (P0 reference)

| Command | Purpose |
|---|---|
| `houseofmath init` | Interactive first-run setup. Picks LLM provider, prompts for API key (if any), writes `houseofmath.config.yaml`. |
| `houseofmath run [--topic T] [--level L] [--grade G] [--count N]` | Launch the Streamlit app in the browser. **All end-user actions happen in the UI from this point on** — picking a topic, taking the test, reviewing answers, viewing history, retaking. Flags are optional pre-fills for the Home screen; if omitted, the UI handles selection. |
| `houseofmath list` | Print the topic / level / grade matrix to the terminal. (The same info is browsable inside the UI's Home screen — this command is mainly for scripting.) |
| `houseofmath stats` | Print progress summary to terminal. (Full interactive stats live inside the UI's Stats screen.) |
| `houseofmath generate --topic T --level L [--grade G] [--count N]` | LLM-generates N candidate questions into `Question Bank/_pending/<topic>/<level>.json`. Requires an LLM provider configured (not `none`). |
| `houseofmath promote <question_id>` | Move a reviewed question from `_pending/` into the live bank. Runs `validate` first. |
| `houseofmath add` | Interactive guided flow for hand-authoring a single question. Walks through every required field, runs validation, writes to the appropriate file. |
| `houseofmath validate [path]` | Lint the entire bank (or a single file). Checks JSON schema, unique IDs, options length, correct-index range, LaTeX parseability. **Required to pass in CI before any PR merges.** |
| `houseofmath doctor` | Diagnostic. Checks Python version, installed dependencies, config validity, LLM connectivity, bank validation status. First thing to run when something breaks. |

---

## 9. Question Bank Generation (P0 strategy)

Two complementary paths, both human-reviewed before live merge.

### 9.1 `houseofmath generate` (LLM-authored)
```bash
houseofmath generate --topic algebra --level medium --grade 7 --count 50
```
- Calls the configured LLM with a strict prompt template that enforces the JSON schema
- Output lands in `Question Bank/_pending/algebra/medium.json`
- Maintainer / contributor reviews each question, edits as needed
- `houseofmath promote <id>` moves approved questions into the live bank
- The LLM **never** writes directly to the live bank

The generation prompt template lives at `houseofmath/prompts/generate.md` and includes:
- The JSON schema spec
- Grade-appropriate calibration guidance
- Examples of well-formed questions for the topic
- Explicit instruction to provide a static `explanation` so questions remain useful offline

### 9.2 Public dataset importers
One-off Python scripts under `scripts/importers/`:
- `import_openstax.py` — OpenStax prealgebra & elementary algebra (CC-BY-4.0)
- `import_ck12.py` — CK-12 FlexBooks (CC-BY-NC-4.0; flag NC license in metadata)

Importers must:
- Map source content into the question schema
- Populate `source` and `license` fields
- Output to `_pending/` for human review (importers don't write to live bank either)
- Be idempotent (re-running doesn't duplicate IDs)

P1 contribution opportunity: importers for NCERT exemplar problems, MATH dataset, GSM8K (filtered).

---

## 10. Validation Rules (`houseofmath validate`)

Must enforce on every PR:
- JSON parses cleanly
- Every question matches the schema in `houseofmath/validation/schema.py`
- `id` values are unique across the entire bank
- `options` array has exactly 4 entries
- `correct` is an integer in `[0, 3]`
- `grade` is `null` or in `[3, 9]`
- `explanation` is non-empty
- LaTeX in `question`, `options`, and `explanation` parses without errors (use `pylatexenc` or similar)
- `source` and `license` populated when the file is under a known importer-owned section

This runs in CI via GitHub Actions.

---

## 11. Progress Tracking

Local SQLite at `~/.houseofmath/history.db`.

Schema:
```sql
CREATE TABLE sessions (
  id INTEGER PRIMARY KEY,
  started_at TIMESTAMP,
  topic TEXT,
  level TEXT,
  grade INTEGER,
  score INTEGER,
  total INTEGER,
  duration_seconds INTEGER
);

CREATE TABLE attempts (
  id INTEGER PRIMARY KEY,
  session_id INTEGER REFERENCES sessions(id),
  question_id TEXT,
  user_answer INTEGER,
  correct INTEGER,
  is_correct BOOLEAN,
  tags TEXT  -- comma-joined for simple weak-area analysis
);
```

Powers `houseofmath stats` and feeds the Reporter's personalized feedback when an LLM is connected.

---

## 12. Streamlit Frontend (`houseofmath/app/streamlit_app.py`)

**Design principle: once the user runs `houseofmath run`, the browser is the only interface they ever need.** No going back to the terminal between sessions, to view history, to retake tests, or to read explanations. Everything the end user does happens in the UI.

The Streamlit app is a single-page app with screens routed via `st.session_state.screen`. A persistent left sidebar lets users navigate between screens at any time and shows the active LLM provider.

### 12.1 Screens

**1. Home / Setup screen** *(default landing)*
- Topic dropdown (populated from `Question Bank/`)
- Level radio buttons (easy / medium / difficult)
- Grade dropdown (3–9, plus "Any")
- Question count slider (default 10, range 5–25)
- "Start Practice" button — launches the test
- Recent sessions panel showing the last 5 attempts with scores, click any to jump to its Review screen
- Active LLM provider badge (e.g. "Connected: claude-code" or "Offline mode")

**2. Test screen**
- One question at a time, MathJax/LaTeX rendered
- Progress indicator (e.g., "Question 3 of 10")
- Radio buttons for the 4 options
- "Next" button advances; "Previous" allows revisiting earlier questions before submission
- "Submit Test" button (always available, with confirmation modal)
- No hints. No timer.

**3. Submit confirmation**
- Modal-style prompt: "Submit your answers? You answered X of Y questions."
- Confirm or cancel.

**4. Review screen**
- Top: score banner (e.g., "7 / 10 correct") + tag-level breakdown chart (which sub-skills you got right/wrong)
- Reporter summary panel: templated by default, LLM-generated paragraph if a provider is connected. Includes weak-area callouts and suggested next topics.
- Per-question accordion list: each question expandable, showing user's answer (✓ or ✗), correct answer, and the static explanation
- **Tutor "Explain differently" button** per question — only visible if LLM provider is connected. Clicking calls Tutor, streams a rephrased explanation in-place
- "Retake this test" button (same questions, fresh attempt)
- "Try a new topic" button (returns to Home)

**5. Stats / History screen** *(accessible from sidebar at any time)*
- Score-over-time line chart per topic
- Total sessions, lifetime accuracy, best topic, weakest topic
- Filterable session log (by topic, level, grade, date range)
- Click any past session to load its Review screen
- "Export history (CSV)" button

**6. Settings screen** *(accessible from sidebar)*
- Shows current LLM provider and model (read-only — actual config edits still happen via `houseofmath init` in the terminal)
- Link to the config file location
- "Test LLM connection" button — sends a hello-world prompt and shows the response, useful for verifying setup

### 12.2 What is NOT in the UI

These remain CLI-only because they are contributor / admin operations, not end-user actions:
- `houseofmath init` — initial setup (must run before first launch)
- `houseofmath generate` — bulk LLM question authoring
- `houseofmath add` — manually add a question
- `houseofmath promote` — move pending questions to the live bank
- `houseofmath validate` — schema linter
- `houseofmath doctor` — environment diagnostic

Everything else — taking tests, reviewing, viewing stats, retaking, switching topics, calling the Tutor — happens in the browser.

### 12.3 Implementation notes

LaTeX rendering uses Streamlit's native `st.markdown` with `$...$` syntax (or `st.latex` for block equations).

Launched by the CLI via `streamlit run houseofmath/app/streamlit_app.py`. The CLI does NOT pass a pre-selected session — the UI's Home screen handles topic/level/grade selection. Optional CLI flags (`--topic`, `--level`, `--grade`) are passed through as Home-screen defaults so power users can shortcut to a specific configuration, but the UI is fully self-sufficient if launched with no flags.

Cross-screen state (current question set, user answers, history queries) lives in `st.session_state`. Persistent state (history, settings) reads from `~/.houseofmath/history.db` and `houseofmath.config.yaml` on every page load — the user can edit config in another terminal and refresh the browser to pick it up.

---

## 13. Tech Stack Summary

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | Matches project ecosystem; broad LLM SDK support |
| CLI | Click | Standard, ergonomic, good help text |
| Frontend | Streamlit | Fastest path to a working browser UI; native LaTeX |
| Storage | SQLite (stdlib) | Zero-deps progress tracking |
| LLM SDKs | `anthropic`, `openai`, `google-generativeai`, `httpx` (Ollama), `subprocess` (Claude Code) | Optional installs via extras |
| Validation | `pydantic` + `pylatexenc` | Schema + LaTeX sanity |
| Tests | `pytest` | Standard |
| CI | GitHub Actions | Run `validate` + `pytest` on every PR |

`pyproject.toml` extras:
```toml
[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]
openai = ["openai>=1.0"]
gemini = ["google-generativeai>=0.8"]
# claude-code and ollama have no SDK dependencies — they use subprocess and httpx (already in core)
all = ["houseofmath[anthropic,openai,gemini]"]
```

---

## 14. Contributing Workflow

Documented in `CONTRIBUTING.md`. Summary for the build doc:

1. Fork the repo
2. Add or generate questions:
   - `houseofmath add` for a single hand-authored question
   - `houseofmath generate ...` for LLM-drafted batches (review each one)
   - Importer scripts for public datasets
3. Run `houseofmath validate` locally — must pass
4. Open a PR; CI runs `validate` + `pytest`
5. Maintainer reviews question quality and merges

PR template includes:
- Source / license of new questions
- Sample IDs for spot-check
- Confirmation `validate` passes locally

---

## 15. P0 Acceptance Checklist

The repo is P0-ready when all of these are true:
- [ ] `pip install -e .` works on a fresh clone
- [ ] `houseofmath init` writes a valid config with `provider: none` as default
- [ ] `houseofmath run` launches Streamlit; user can complete an entire session (pick topic → take test → review → view history → retake) **without ever returning to the terminal**
- [ ] Home screen lets the user pick topic / level / grade / count and start a test
- [ ] Test screen runs a 10-question session end-to-end with no LLM connected
- [ ] Review screen shows per-question correctness, full explanations, Reporter summary, and "Explain differently" button (when LLM connected)
- [ ] Stats screen shows score trends, lifetime accuracy, weak topics, and a clickable session log
- [ ] Settings screen shows current LLM provider and offers a "Test connection" button
- [ ] Sidebar nav lets the user jump between Home / Stats / Settings at any time
- [ ] Question Bank seeded with at least 20 questions per topic/level (grade-tagged where natural) via `generate` + importers, all human-reviewed
- [ ] LaTeX renders correctly in question, options, and explanation
- [ ] `~/.houseofmath/history.db` is created on first run and logs sessions
- [ ] `houseofmath validate` passes on the entire bank
- [ ] `houseofmath doctor` reports green
- [ ] All six LLM adapters (`none`, `claude-code`, `gemini`, `ollama`, `anthropic`, `openai`) implement `LLMClient` and have at least a smoke test
- [ ] `houseofmath init` correctly auto-detects an authenticated Claude Code installation and recommends `claude-code` when present
- [ ] README's "Connect your LLM" section clearly shows Claude subscribers the `claude-code` path and is honest about ChatGPT Plus / Gemini Advanced not being supported
- [ ] `README.md`, `LICENSE` (MIT), `CONTRIBUTING.md` present
- [ ] CI runs `validate` + `pytest` on every PR

---

## 16. License

MIT. Contributed questions retain their source license metadata; the bank as a whole is redistributable under MIT for original content and the source license for imported content (importer enforces correct attribution).
