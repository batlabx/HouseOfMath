# HouseOfMath

> An open-source, BYO-LLM math practice agent. Pick a topic, level, and grade — get a 10-question MCQ practice test in your browser. Works offline by default.

[![CI](https://github.com/batlabx/HouseOfMath/actions/workflows/ci.yml/badge.svg)](https://github.com/batlabx/HouseOfMath/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

HouseOfMath is a Python CLI tool that runs a local Streamlit app delivering multiple-choice math practice tests for **grades 3 through 9**. Questions live in a version-controlled `Question Bank/` folder inside the repo. The LLM is **optional** — the core practice loop works fully offline using static hints and explanations that ship with each question.

Connecting an LLM (Claude, OpenAI, local Ollama, etc.) unlocks personalized post-test feedback and a richer Reporter summary.

---

## Quickstart

HouseOfMath needs **Python 3.10 or newer**.

### macOS

The system Python on macOS is 3.9 — too old. Easiest path is Homebrew + a virtual environment.

**1. Install Homebrew** (if you don't have it):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After it finishes, run the two `eval` lines it prints under "Next steps" so `brew` is on your PATH.

**2. Install Python 3.12:**

```bash
brew install python@3.12
python3.12 --version          # confirm: Python 3.12.x
```

**3. Clone and install in a venv:**

```bash
git clone https://github.com/batlabx/HouseOfMath
cd HouseOfMath
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

**4. Run it:**

```bash
houseofmath init              # picks LLM provider, defaults to "none"
houseofmath run               # opens the app in your browser
```

Next time you come back, just re-activate the venv before running:

```bash
cd ~/Desktop/HouseofMath
source .venv/bin/activate
houseofmath run
```

To leave the venv when you're done: `deactivate`.

### Linux

Most distros ship Python 3.10+ already. Otherwise install via your package manager (e.g. `sudo apt install python3.12 python3.12-venv`), then:

```bash
git clone https://github.com/batlabx/HouseOfMath
cd HouseOfMath
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip      # PEP 660 editable installs need pip ≥ 21.3
pip install -e .
houseofmath init
houseofmath run
```

### Windows

```powershell
git clone https://github.com/batlabx/HouseOfMath
cd HouseOfMath
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
houseofmath init
houseofmath run
```

### Non-interactive shortcut

Once installed, you can skip the Home screen and jump straight to a configured test:

```bash
houseofmath run --topic algebra --level medium --grade 7
```

Once you run `houseofmath run`, the browser is the only interface you need: pick a topic, take the test, review answers, view stats, and retake — all in the UI.

### Troubleshooting

- **`pip: command not found`** — use `python3 -m pip ...` (or `pip3`) instead.
- **`ERROR: File "setup.py" or "setup.cfg" not found`** — your `pip` is older than 21.3. Run `python3 -m pip install --upgrade pip` first.
- **`error: externally-managed-environment`** (Homebrew Python on macOS, or recent Debian/Ubuntu) — you skipped the `python -m venv .venv && source .venv/bin/activate` step. Don't use `--break-system-packages`; use the venv.
- **`Package 'houseofmath' requires a different Python: 3.9.6 not in '>=3.10'`** — you're on the system Python. Install 3.10+ via Homebrew (macOS) or your package manager and use that explicit version (`python3.12 -m venv .venv`).
- **`zsh: command not found: houseofmath`** — your venv isn't activated. Run `source .venv/bin/activate` from the project root.

---

## Connect your LLM

HouseOfMath supports six provider options so you can connect using whatever you already have — a Claude subscription, a free API key, a paid API, a local model, or nothing at all.

| Option | Cost | Account needed | Notes |
|---|---|---|---|
| `none` | Free | None | Fully offline. Static explanations only. **Default.** |
| `claude-code` | Covered by **Claude Pro/Max subscription** | Anthropic account + Claude Code installed | Recommended for Claude subscribers. No separate API key. |
| `gemini` | **Free tier** (15 req/min, 1M tokens/day) | Google account | No credit card required. Best zero-cost LLM option. |
| `ollama` | Free | None | Runs locally. Requires Ollama installed + a model pulled. |
| `anthropic` | Pay-per-use API | Anthropic API key with billing | Separate from Claude Pro subscription. |
| `openai` | Pay-per-use API | OpenAI API key with billing | See note below. |

**Not supported (and why):** ChatGPT Plus, Gemini Advanced (subscription tier), GitHub Copilot, Cursor, and similar consumer subscriptions do not expose programmatic access. There is no honest, ToS-compliant way to use them from a CLI tool. Users with these subscriptions should pick `gemini` (free tier), `claude-code` (if they also have a Claude subscription), or `ollama`.

> **Note:** ChatGPT Plus/Pro subscriptions do NOT grant API access — these are separate products. The `openai` provider needs an API key with billing enabled at platform.openai.com.

### Recommended path for Claude Pro/Max subscribers

You already pay for Claude. Use it.

```bash
# 1. Install Claude Code (one-time)
npm install -g @anthropic-ai/claude-code

# 2. Authenticate (uses your subscription, no API key)
claude /login

# 3. Configure HouseOfMath
houseofmath init        # auto-detects Claude Code, suggests `claude-code`
```

HouseOfMath shells out to your authenticated `claude` CLI — your credentials never touch this codebase.

---

## CLI reference

| Command | Purpose |
|---|---|
| `houseofmath init` | Interactive first-run setup. Picks LLM provider, prompts for API key (if any), writes `houseofmath.config.yaml`. |
| `houseofmath run [--topic T] [--level L] [--grade G] [--count N]` | Launch the Streamlit app in the browser. |
| `houseofmath list` | Print the topic / level / grade matrix to the terminal. |
| `houseofmath stats` | Print progress summary to terminal. |
| `houseofmath generate --topic T --level L [--grade G] [--count N]` | LLM-generates N candidate questions into `Question Bank/_pending/<topic>/<level>.json`. Requires an LLM provider configured (not `none`). |
| `houseofmath promote <question_id>` | Move a reviewed question from `_pending/` into the live bank. Runs `validate` first. |
| `houseofmath add` | Interactive guided flow for hand-authoring a single question. |
| `houseofmath validate [path]` | Lint the entire bank (or a single file). |
| `houseofmath doctor` | Diagnostic. Checks Python version, dependencies, config, LLM connectivity, bank validity. |

---

## Architecture

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

Three subagents (Curator, Tutor, Reporter), one CLI, one Streamlit frontend, one SQLite store.

---

## Question Bank

Each topic/level pair is a JSON file in `Question Bank/<topic>/<level>.json`:

```json
[
  {
    "id": "alg-easy-001",
    "grade": 6,
    "question": "Solve for $x$: $2x + 6 = 14$",
    "options": ["$x = 2$", "$x = 4$", "$x = 6$", "$x = 8$"],
    "correct": 1,
    "tags": ["linear-equations", "one-variable"],
    "explanation": "Subtract 6 from both sides: $2x = 8$. Divide by 2: $x = 4$.",
    "source": "openstax-prealgebra-ch3",
    "license": "CC-BY-4.0"
  }
]
```

Schema is enforced by `houseofmath validate` (and CI on every PR).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version:

1. Fork the repo
2. Add or generate questions:
   - `houseofmath add` for a single hand-authored question
   - `houseofmath generate ...` for LLM-drafted batches (review each one)
   - Importer scripts under `scripts/importers/` for public datasets
3. Run `houseofmath validate` locally — must pass
4. Open a PR; CI runs `validate` + `pytest`

---

## License

MIT — see [LICENSE](LICENSE). Contributed questions retain their source license metadata in the `license` field; the importer enforces correct attribution.
