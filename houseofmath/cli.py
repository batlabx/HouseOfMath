"""Click CLI — every command from section 8 of the build instructions."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

import click

from . import __version__
from .config import (
    CONFIG_FILENAME,
    config_path,
    example_config_path,
    history_db_path,
    load_config,
    question_bank_path,
    save_config,
)
from .curator import list_topics, topic_matrix
from .llm.factory import PROVIDERS, autodetect, get_client
from .storage import History
from .validation.schema import LEVELS, Question, validate_bank, validate_file


@click.group(help="HouseOfMath — math practice in your browser.")
@click.version_option(__version__, prog_name="houseofmath")
def main() -> None:
    pass


# ---------- init ----------


@main.command(help="Interactive first-run setup. Picks LLM provider, writes config.")
def init() -> None:
    detected = autodetect()
    click.echo(f"Detected provider: {click.style(detected, fg='green', bold=True)}")
    click.echo("\nAvailable providers:")
    for p in PROVIDERS:
        marker = " (recommended)" if p == detected else ""
        click.echo(f"  - {p}{marker}")

    provider = click.prompt(
        "\nWhich provider?",
        default=detected,
        type=click.Choice(PROVIDERS),
        show_choices=False,
    )

    cfg: dict = {"provider": provider}

    if provider == "claude-code":
        binary = click.prompt("Claude Code binary name/path", default="claude")
        model = click.prompt(
            "Model (blank to let Claude Code choose)",
            default="",
            show_default=False,
        )
        cfg["claude-code"] = {"binary": binary}
        if model:
            cfg["claude-code"]["model"] = model
        if not shutil.which(binary):
            click.secho(
                f"Note: `{binary}` is not on PATH. Install Claude Code and run `claude /login`.",
                fg="yellow",
            )

    elif provider == "anthropic":
        cfg["anthropic"] = {
            "model": click.prompt("Model", default="claude-sonnet-4-6"),
            "api_key_env": click.prompt("Env var for API key", default="ANTHROPIC_API_KEY"),
        }
    elif provider == "openai":
        cfg["openai"] = {
            "model": click.prompt("Model", default="gpt-4o-mini"),
            "api_key_env": click.prompt("Env var for API key", default="OPENAI_API_KEY"),
        }
    elif provider == "gemini":
        cfg["gemini"] = {
            "model": click.prompt("Model", default="gemini-2.0-flash"),
            "api_key_env": click.prompt("Env var for API key", default="GOOGLE_AI_API_KEY"),
        }
    elif provider == "ollama":
        cfg["ollama"] = {
            "base_url": click.prompt("Base URL", default="http://localhost:11434"),
            "model": click.prompt("Model", default="llama3"),
        }

    path = save_config(cfg)
    click.secho(f"\nWrote {path}", fg="green")
    if provider != "none":
        click.echo("Try `houseofmath doctor` to verify the connection.")


# ---------- run ----------


@main.command(help="Launch the Streamlit app in your browser.")
@click.option("--topic", default=None, help="Pre-fill the Home screen topic.")
@click.option("--level", default=None, type=click.Choice(LEVELS), help="Pre-fill level.")
@click.option("--grade", default=None, type=click.IntRange(3, 9), help="Pre-fill grade.")
@click.option("--count", default=10, type=click.IntRange(1, 50), help="Pre-fill question count.")
def run(topic: str | None, level: str | None, grade: int | None, count: int) -> None:
    app_path = Path(__file__).parent / "app" / "streamlit_app.py"
    args = ["streamlit", "run", str(app_path), "--"]
    if topic:
        args += ["--topic", topic]
    if level:
        args += ["--level", level]
    if grade:
        args += ["--grade", str(grade)]
    if count:
        args += ["--count", str(count)]
    click.echo(f"Launching: {' '.join(args)}")
    try:
        subprocess.run(args, check=True)
    except FileNotFoundError:
        click.secho(
            "streamlit is not installed. Reinstall HouseOfMath: `pip install -e .`",
            fg="red",
        )
        sys.exit(1)


# ---------- list ----------


@main.command("list", help="Print the topic / level / grade matrix to the terminal.")
def list_cmd() -> None:
    bank = question_bank_path()
    matrix = topic_matrix(bank)
    if not matrix:
        click.secho(f"No topics found in {bank}.", fg="yellow")
        return
    click.echo(f"Question Bank @ {bank}")
    header = f"  {'topic':<14} " + " ".join(f"{lvl:>10}" for lvl in LEVELS)
    click.echo(header)
    click.echo("  " + "-" * (len(header) - 2))
    for topic, per_level in matrix.items():
        row = f"  {topic:<14} " + " ".join(f"{per_level.get(l, 0):>10}" for l in LEVELS)
        click.echo(row)


# ---------- stats ----------


@main.command(help="Print progress summary to terminal.")
def stats() -> None:
    h = History()
    summary = h.lifetime_summary()
    if summary["sessions"] == 0:
        click.echo("No sessions logged yet. Run `houseofmath run` and finish a test.")
        return
    click.echo(f"Sessions: {summary['sessions']}")
    click.echo(
        f"Lifetime accuracy: {summary['total_correct']}/{summary['total_questions']} "
        f"({summary['lifetime_accuracy']:.0%})"
    )
    if summary["best_topic"]:
        click.echo(f"Best topic: {summary['best_topic']}")
    if summary["weakest_topic"]:
        click.echo(f"Weakest topic: {summary['weakest_topic']}")

    click.echo("\nPer-topic accuracy:")
    for row in h.topic_accuracy():
        click.echo(
            f"  {row['topic']:<14} {row['total_correct']:>4}/{row['total_questions']:<4} "
            f"({row['accuracy']:.0%}) over {row['sessions']} sessions"
        )


# ---------- generate ----------


@main.command(help="LLM-generate candidate questions into Question Bank/_pending/.")
@click.option("--topic", required=True)
@click.option("--level", required=True, type=click.Choice(LEVELS))
@click.option("--grade", default=None, type=click.IntRange(3, 9))
@click.option("--count", default=10, type=click.IntRange(1, 50))
def generate(topic: str, level: str, grade: int | None, count: int) -> None:
    cfg = load_config()
    if cfg.get("provider", "none") == "none":
        click.secho(
            "No LLM provider configured. Run `houseofmath init` and pick something other than 'none'.",
            fg="red",
        )
        sys.exit(1)

    client = get_client(cfg)
    if not client.is_available():
        click.secho(
            f"Provider `{cfg['provider']}` is not reachable. Run `houseofmath doctor` to debug.",
            fg="red",
        )
        sys.exit(1)

    try:
        prompt_template = resources.files("houseofmath.prompts").joinpath("generate.md").read_text(
            encoding="utf-8"
        )
    except (FileNotFoundError, ModuleNotFoundError):
        prompt_template = "Generate questions in JSON matching the schema in instructions.md."

    user_prompt = (
        f"{prompt_template}\n\n"
        f"Generate exactly {count} questions for topic='{topic}', level='{level}'"
        + (f", grade={grade}" if grade else "")
        + ".\n"
        "Reply with ONLY a JSON array — no commentary, no markdown fences."
    )

    click.echo(f"Generating {count} {level} questions for {topic} via {cfg['provider']}...")
    raw = client.chat(
        [
            {
                "role": "system",
                "content": "You generate strict-schema math practice questions for grades 3-9.",
            },
            {"role": "user", "content": user_prompt},
        ]
    )
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    try:
        candidates = json.loads(raw)
    except json.JSONDecodeError as e:
        click.secho(f"LLM did not return valid JSON: {e}", fg="red")
        click.echo(raw[:1000])
        sys.exit(2)

    out_dir = question_bank_path() / "_pending" / topic
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{level}.json"
    existing: list = []
    if out_file.exists():
        existing = json.loads(out_file.read_text(encoding="utf-8"))
    merged = existing + candidates
    out_file.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    click.secho(
        f"Wrote {len(candidates)} candidates to {out_file} "
        f"({len(merged)} total pending). Review with `houseofmath validate {out_file}` and promote individually.",
        fg="green",
    )


# ---------- promote ----------


@main.command(help="Promote a reviewed question from _pending/ into the live bank.")
@click.argument("question_id")
def promote(question_id: str) -> None:
    bank = question_bank_path()
    pending_root = bank / "_pending"
    if not pending_root.exists():
        click.secho("No _pending/ directory.", fg="red")
        sys.exit(1)

    found: tuple[Path, dict, int] | None = None
    for f in pending_root.rglob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for i, item in enumerate(data):
            if isinstance(item, dict) and item.get("id") == question_id:
                found = (f, item, i)
                break
        if found:
            break

    if not found:
        click.secho(f"Question id={question_id} not found in _pending/.", fg="red")
        sys.exit(1)

    src_file, q_dict, idx = found
    parts = src_file.relative_to(pending_root).parts  # topic/level.json
    topic, level_file = parts[0], parts[1]
    level = level_file.replace(".json", "")
    if level not in LEVELS:
        click.secho(f"Cannot infer level from {src_file}", fg="red")
        sys.exit(1)

    try:
        Question(**q_dict)
    except Exception as e:  # noqa: BLE001
        click.secho(f"Cannot promote — question fails validation: {e}", fg="red")
        sys.exit(2)

    target_file = bank / topic / f"{level}.json"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    live = json.loads(target_file.read_text(encoding="utf-8")) if target_file.exists() else []
    if any(q.get("id") == question_id for q in live):
        click.secho(f"id={question_id} already exists in {target_file}.", fg="red")
        sys.exit(1)
    live.append(q_dict)
    target_file.write_text(json.dumps(live, indent=2), encoding="utf-8")

    src_data = json.loads(src_file.read_text(encoding="utf-8"))
    src_data.pop(idx)
    src_file.write_text(json.dumps(src_data, indent=2), encoding="utf-8")

    click.secho(f"Promoted {question_id} -> {target_file}", fg="green")


# ---------- add ----------


@main.command(help="Interactive guided flow for hand-authoring a single question.")
def add() -> None:
    bank = question_bank_path()
    topics = list_topics(bank) or ["algebra", "arithmetic", "geometry", "fractions", "percentages"]
    topic = click.prompt("Topic", type=click.Choice(topics, case_sensitive=False))
    level = click.prompt("Level", type=click.Choice(LEVELS))
    grade_raw = click.prompt("Grade (3-9, or blank for grade-agnostic)", default="", show_default=False)
    grade: int | None = int(grade_raw) if grade_raw.strip() else None

    target = bank / topic / f"{level}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else []

    prefix_map = {
        "algebra": "alg",
        "arithmetic": "arith",
        "geometry": "geo",
        "fractions": "frac",
        "percentages": "pct",
    }
    prefix = prefix_map.get(topic, topic[:4])
    next_seq = len(existing) + 1
    default_id = f"{prefix}-{level}-{next_seq:03d}"
    qid = click.prompt("Question ID", default=default_id)

    question = click.prompt("Question (Markdown + LaTeX)").strip()
    options = [click.prompt(f"Option {i + 1}").strip() for i in range(4)]
    correct = click.prompt("Correct option index (0-3)", type=click.IntRange(0, 3))
    explanation = click.prompt("Explanation").strip()
    tags_raw = click.prompt("Tags (comma-separated, lowercase-hyphenated)", default="")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    source = click.prompt("Source", default="houseofmath-handcrafted")
    license_ = click.prompt("License", default="MIT")

    candidate = {
        "id": qid,
        "grade": grade,
        "question": question,
        "options": options,
        "correct": correct,
        "tags": tags,
        "explanation": explanation,
        "source": source,
        "license": license_,
    }

    try:
        Question(**candidate)
    except Exception as e:  # noqa: BLE001
        click.secho(f"Validation failed: {e}", fg="red")
        sys.exit(2)

    existing.append(candidate)
    target.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    click.secho(f"Added {qid} -> {target}", fg="green")


# ---------- validate ----------


@main.command(help="Lint the entire bank (or a single file).")
@click.argument("path", required=False, type=click.Path(exists=True))
def validate(path: str | None) -> None:
    if path:
        p = Path(path)
        if p.is_file():
            _, errs = validate_file(p)
            if not errs:
                click.secho(f"OK — {p}", fg="green")
                sys.exit(0)
            for e in errs:
                click.echo(e)
            sys.exit(1)
        report = validate_bank(p)
    else:
        report = validate_bank(question_bank_path())
    click.echo(report.summary())
    sys.exit(0 if report.ok else 1)


# ---------- doctor ----------


@main.command(help="Diagnostic. Run this first when something breaks.")
def doctor() -> None:
    ok = True

    click.echo(f"Python:       {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        click.secho("  ✗ Need Python 3.10+", fg="red")
        ok = False

    for mod in ("click", "streamlit", "pydantic", "yaml", "pylatexenc", "httpx"):
        try:
            __import__(mod if mod != "yaml" else "yaml")
            click.echo(f"  ✓ {mod}")
        except ImportError:
            click.secho(f"  ✗ {mod} not installed", fg="red")
            ok = False

    cfg_p = config_path()
    if cfg_p.exists():
        click.echo(f"Config:       {cfg_p}")
    else:
        click.secho(f"Config:       missing ({cfg_p}). Run `houseofmath init`.", fg="yellow")

    cfg = load_config()
    provider = cfg.get("provider", "none")
    click.echo(f"Provider:     {provider}")
    try:
        client = get_client(cfg)
        if client.is_available():
            click.secho(f"  ✓ {provider} reachable", fg="green")
        else:
            click.secho(f"  ✗ {provider} not reachable / not installed", fg="yellow")
    except Exception as e:  # noqa: BLE001
        click.secho(f"  ✗ Could not initialise provider: {e}", fg="red")
        ok = False

    bank = question_bank_path()
    click.echo(f"Bank:         {bank}")
    report = validate_bank(bank)
    click.echo("  " + report.summary().splitlines()[0])
    if not report.ok:
        ok = False

    db = history_db_path()
    click.echo(f"History DB:   {db} (exists={db.exists()})")

    if ok:
        click.secho("\nAll green.", fg="green")
        sys.exit(0)
    click.secho("\nIssues detected — see above.", fg="yellow")
    sys.exit(1)


if __name__ == "__main__":
    main()
