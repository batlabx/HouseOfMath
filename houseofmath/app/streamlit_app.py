"""Streamlit frontend — the only end-user interface after `houseofmath run`.

Single-page app with screens routed via `st.session_state.screen`. A persistent
sidebar lets users navigate between Home / Stats / Settings at any time.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from houseofmath.config import (
    config_path,
    load_config,
    question_bank_path,
)
from houseofmath.curator import list_topics, select, topic_matrix
from houseofmath.llm.factory import get_client
from houseofmath.reporter import Reporter, TestResult, grade_user_answers
from houseofmath.storage import History
from houseofmath.storage.history import AttemptRow
from houseofmath.tutor import Tutor
from houseofmath.validation.schema import LEVELS

# ---------- bootstrap ----------

st.set_page_config(page_title="HouseOfMath", page_icon="🧮", layout="wide")


def _parse_cli_defaults() -> dict:
    """Parse `streamlit run app.py -- --topic ... --level ... --grade ... --count ...`."""
    if "--" not in sys.argv:
        return {}
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--level", default=None)
    parser.add_argument("--grade", default=None, type=int)
    parser.add_argument("--count", default=None, type=int)
    idx = sys.argv.index("--")
    args, _ = parser.parse_known_args(sys.argv[idx + 1 :])
    return {k: v for k, v in vars(args).items() if v is not None}


CLI_DEFAULTS = _parse_cli_defaults()


def _ss_init() -> None:
    defaults = {
        "screen": "home",
        "topic": CLI_DEFAULTS.get("topic"),
        "level": CLI_DEFAULTS.get("level", "easy"),
        "grade": CLI_DEFAULTS.get("grade"),
        "count": CLI_DEFAULTS.get("count", 10),
        "qset": None,
        "current_q": 0,
        "user_answers": {},  # idx -> chosen index
        "started_at": None,
        "duration_seconds": None,
        "submit_confirm": False,
        "viewing_session": None,  # session id when reviewing a past session
        "rephrased": {},  # qid -> rephrased text
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


_ss_init()


@st.cache_resource
def _history() -> History:
    return History()


@st.cache_data(ttl=10)
def _topics_cached(bank_str: str) -> list[str]:
    return list_topics(Path(bank_str))


@st.cache_data(ttl=10)
def _matrix_cached(bank_str: str) -> dict:
    return topic_matrix(Path(bank_str))


cfg = load_config()
provider = cfg.get("provider", "none")
client = get_client(cfg)
tutor = Tutor(client if provider != "none" else None)
reporter = Reporter(client if provider != "none" else None, _history())

bank = question_bank_path()


# ---------- sidebar ----------


def _sidebar() -> None:
    st.sidebar.title("🧮 HouseOfMath")
    st.sidebar.markdown("---")
    if st.sidebar.button("🏠 Home", use_container_width=True):
        st.session_state.screen = "home"
        st.rerun()
    if st.sidebar.button("📊 Stats", use_container_width=True):
        st.session_state.screen = "stats"
        st.rerun()
    if st.sidebar.button("⚙️ Settings", use_container_width=True):
        st.session_state.screen = "settings"
        st.rerun()
    st.sidebar.markdown("---")
    badge = (
        f"🟢 Connected: `{provider}`"
        if provider != "none"
        else "🟡 Offline mode (no LLM)"
    )
    st.sidebar.markdown(badge)


_sidebar()


# ---------- screens ----------


def screen_home() -> None:
    st.title("🧮 HouseOfMath")
    st.markdown(
        "Pick a topic, level, and grade. Take a 10-question multiple-choice test. Review your answers."
    )

    topics = _topics_cached(str(bank))
    if not topics:
        st.error(
            f"No topics found in `{bank}`. Add some questions under "
            "`Question Bank/<topic>/<level>.json` and refresh."
        )
        return

    matrix = _matrix_cached(str(bank))
    default_topic = (
        st.session_state.topic
        if st.session_state.topic in topics
        else topics[0]
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        topic = st.selectbox(
            "Topic", topics, index=topics.index(default_topic), key="home_topic"
        )
    with col2:
        level_idx = LEVELS.index(st.session_state.level) if st.session_state.level in LEVELS else 0
        level = st.radio("Level", LEVELS, index=level_idx, horizontal=True, key="home_level")
    with col3:
        grade_options = ["Any"] + [str(g) for g in range(3, 10)]
        grade_default = "Any" if st.session_state.grade is None else str(st.session_state.grade)
        grade_choice = st.selectbox(
            "Grade", grade_options, index=grade_options.index(grade_default), key="home_grade"
        )

    count = st.slider(
        "Number of questions",
        min_value=5,
        max_value=25,
        value=int(st.session_state.count or 10),
        step=1,
        key="home_count",
    )

    available = matrix.get(topic, {}).get(level, 0)
    st.caption(f"{available} question(s) available for `{topic}` / `{level}`.")

    if st.button("▶️ Start Practice", type="primary", use_container_width=True):
        if available == 0:
            st.error("No questions in that topic/level yet. Pick another or add some.")
            return
        try:
            grade = None if grade_choice == "Any" else int(grade_choice)
            qset = select(
                bank,
                topic,
                level,
                grade=grade,
                count=count,
            )
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not load questions: {e}")
            return
        st.session_state.qset = qset
        st.session_state.topic = topic
        st.session_state.level = level
        st.session_state.grade = grade
        st.session_state.count = count
        st.session_state.user_answers = {}
        st.session_state.current_q = 0
        st.session_state.started_at = time.time()
        st.session_state.submit_confirm = False
        st.session_state.viewing_session = None
        st.session_state.rephrased = {}
        st.session_state.screen = "test"
        st.rerun()

    st.markdown("---")
    st.subheader("Recent sessions")
    recent = _history().recent_sessions(limit=5)
    if not recent:
        st.caption("No sessions yet — finish a test to see history here.")
    else:
        for s in recent:
            cols = st.columns([2, 2, 1, 1, 1, 2])
            cols[0].markdown(f"**{s.topic}** / {s.level}")
            cols[1].caption(s.started_at)
            cols[2].markdown(f"Grade: {s.grade or '—'}")
            cols[3].markdown(f"{s.score}/{s.total}")
            pct = (s.score / s.total) if s.total else 0
            cols[4].markdown(f"{pct:.0%}")
            if cols[5].button("Review", key=f"recent_{s.id}"):
                st.session_state.viewing_session = s.id
                st.session_state.screen = "review"
                st.rerun()


def screen_test() -> None:
    qset = st.session_state.qset
    if not qset:
        st.session_state.screen = "home"
        st.rerun()
        return

    if st.session_state.submit_confirm:
        return _submit_modal()

    idx = st.session_state.current_q
    total = qset.total
    q = qset.questions[idx]

    st.progress((idx + 1) / total, text=f"Question {idx + 1} of {total}")
    st.markdown(f"### {q.question}")

    current = st.session_state.user_answers.get(idx)
    choice = st.radio(
        "Choose one:",
        list(range(4)),
        index=current if current is not None else None,
        format_func=lambda i: q.options[i],
        key=f"choice_{idx}",
    )
    if choice is not None:
        st.session_state.user_answers[idx] = choice

    cols = st.columns([1, 1, 1, 2])
    if cols[0].button("◀ Previous", disabled=idx == 0):
        st.session_state.current_q = max(0, idx - 1)
        st.rerun()
    if cols[1].button("Next ▶", disabled=idx >= total - 1):
        st.session_state.current_q = min(total - 1, idx + 1)
        st.rerun()
    if cols[3].button("✅ Submit Test", type="primary"):
        st.session_state.submit_confirm = True
        st.rerun()

    st.caption(f"Answered: {len(st.session_state.user_answers)} / {total}")


def _submit_modal() -> None:
    qset = st.session_state.qset
    answered = len(st.session_state.user_answers)
    st.warning(f"Submit your answers? You answered {answered} of {qset.total} questions.")
    cols = st.columns(2)
    if cols[0].button("Submit", type="primary"):
        _do_submit()
    if cols[1].button("Cancel"):
        st.session_state.submit_confirm = False
        st.rerun()


def _do_submit() -> None:
    qset = st.session_state.qset
    started = st.session_state.started_at or time.time()
    duration = int(time.time() - started)
    user_answers = [st.session_state.user_answers.get(i, -1) for i in range(qset.total)]
    score = grade_user_answers(qset.questions, user_answers)
    st.session_state.duration_seconds = duration

    attempts = [
        AttemptRow(
            session_id=0,
            question_id=q.id,
            user_answer=ua,
            correct=q.correct,
            is_correct=ua == q.correct,
            tags=q.tags,
        )
        for q, ua in zip(qset.questions, user_answers)
    ]
    sid = _history().record_session(
        topic=qset.topic,
        level=qset.level,
        grade=qset.grade,
        score=score,
        total=qset.total,
        duration_seconds=duration,
        attempts=attempts,
        started_at=datetime.utcfromtimestamp(started),
    )
    st.session_state.viewing_session = sid
    st.session_state.submit_confirm = False
    st.session_state.screen = "review"
    st.rerun()


def screen_review() -> None:
    qset = st.session_state.qset
    sid = st.session_state.viewing_session
    h = _history()

    if qset and sid and any(s.id == sid for s in h.recent_sessions(limit=50)):
        # Just-completed session: use the in-memory qset
        user_answers = [st.session_state.user_answers.get(i, -1) for i in range(qset.total)]
        score = grade_user_answers(qset.questions, user_answers)
        result = TestResult(
            topic=qset.topic,
            level=qset.level,
            grade=qset.grade,
            score=score,
            total=qset.total,
            duration_seconds=st.session_state.duration_seconds or 0,
            questions=list(qset.questions),
            user_answers=user_answers,
        )
        _render_review(result)
        return

    if sid:
        # Loading from history: rebuild what we can from DB attempts
        all_sessions = h.all_sessions()
        match = next((s for s in all_sessions if s.id == sid), None)
        if not match:
            st.error("Session not found.")
            if st.button("Back to Home"):
                st.session_state.screen = "home"
                st.rerun()
            return
        attempts = h.attempts_for(sid)
        st.title(f"Session #{sid} — {match.topic} / {match.level}")
        st.markdown(
            f"**Score:** {match.score}/{match.total} "
            f"({(match.score / match.total) * 100:.0f}%)"
            if match.total
            else "No attempts."
        )
        st.markdown(f"**Date:** {match.started_at}  •  **Duration:** {match.duration_seconds}s")
        st.markdown("---")
        st.markdown("### Per-question record")
        for i, a in enumerate(attempts):
            mark = "✅" if a.is_correct else "❌"
            with st.expander(
                f"{mark} Q{i + 1} — {a.question_id}  (your answer: {a.user_answer}, correct: {a.correct})"
            ):
                st.caption(f"Tags: {', '.join(a.tags) if a.tags else '—'}")
        if st.button("Back to Home"):
            st.session_state.viewing_session = None
            st.session_state.screen = "home"
            st.rerun()
        return

    st.info("Nothing to review.")
    if st.button("Back to Home"):
        st.session_state.screen = "home"
        st.rerun()


def _render_review(result: TestResult) -> None:
    pct = (result.score / result.total) * 100 if result.total else 0
    st.title(f"Score: {result.score} / {result.total} ({pct:.0f}%)")

    st.markdown("### Reporter summary")
    with st.spinner("Generating summary..."):
        summary = reporter.summarize(result)
    st.markdown(summary)

    st.markdown("### Sub-skill breakdown")
    tb = result.tag_breakdown()
    if tb:
        df = pd.DataFrame(tb).set_index("tag")[["accuracy"]]
        st.bar_chart(df)
    else:
        st.caption("No tags on these questions.")

    st.markdown("### Per-question review")
    for i, q in enumerate(result.questions):
        ua = result.user_answers[i]
        is_correct = ua == q.correct
        mark = "✅" if is_correct else "❌"
        with st.expander(f"{mark} Q{i + 1}: {q.question}"):
            st.markdown("**Options:**")
            for opt_i, opt in enumerate(q.options):
                indicator = ""
                if opt_i == q.correct:
                    indicator = " ← correct"
                if opt_i == ua and ua != q.correct:
                    indicator = " ← your answer"
                st.markdown(f"- {opt}{indicator}")
            rephrased = st.session_state.rephrased.get(q.id)
            st.markdown("**Explanation:**")
            st.markdown(rephrased or q.explanation)
            if tutor.can_rephrase():
                if st.button("🔄 Explain differently", key=f"rephrase_{q.id}"):
                    with st.spinner("Asking the LLM..."):
                        st.session_state.rephrased[q.id] = tutor.rephrase(q)
                    st.rerun()
            st.caption(f"Tags: {', '.join(q.tags) if q.tags else '—'}")

    cols = st.columns(2)
    if cols[0].button("🔁 Retake this test", type="primary"):
        st.session_state.user_answers = {}
        st.session_state.current_q = 0
        st.session_state.started_at = time.time()
        st.session_state.submit_confirm = False
        st.session_state.rephrased = {}
        st.session_state.screen = "test"
        st.rerun()
    if cols[1].button("🏠 Try a new topic"):
        st.session_state.screen = "home"
        st.rerun()


def screen_stats() -> None:
    h = _history()
    summary = h.lifetime_summary()
    st.title("📊 Stats")
    if summary["sessions"] == 0:
        st.info("No sessions logged yet. Finish a test to see your progress.")
        return

    cols = st.columns(4)
    cols[0].metric("Sessions", summary["sessions"])
    cols[1].metric(
        "Lifetime accuracy",
        f"{summary['lifetime_accuracy']:.0%}",
        f"{summary['total_correct']} / {summary['total_questions']}",
    )
    cols[2].metric("Best topic", summary["best_topic"] or "—")
    cols[3].metric("Weakest topic", summary["weakest_topic"] or "—")

    st.markdown("### Score over time")
    sessions = h.all_sessions()
    df = pd.DataFrame(
        [
            {
                "date": s.started_at,
                "topic": s.topic,
                "score_pct": (s.score / s.total) if s.total else 0,
            }
            for s in sessions
        ]
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        pivot = df.pivot_table(index="date", columns="topic", values="score_pct").ffill()
        st.line_chart(pivot)

    st.markdown("### Per-topic accuracy")
    ta = h.topic_accuracy()
    if ta:
        st.dataframe(pd.DataFrame(ta), use_container_width=True)

    st.markdown("### Per-tag accuracy (weakest first)")
    tag = h.tag_accuracy()
    if tag:
        st.dataframe(pd.DataFrame(tag), use_container_width=True)

    st.markdown("### Session log")
    log_df = pd.DataFrame(
        [
            {
                "id": s.id,
                "started_at": s.started_at,
                "topic": s.topic,
                "level": s.level,
                "grade": s.grade,
                "score": f"{s.score}/{s.total}",
                "duration_s": s.duration_seconds,
            }
            for s in reversed(sessions)
        ]
    )
    st.dataframe(log_df, use_container_width=True, hide_index=True)
    csv = log_df.to_csv(index=False)
    st.download_button("⬇ Export history (CSV)", csv, "houseofmath_history.csv", "text/csv")

    pick = st.number_input("Open session id", min_value=0, value=0, step=1)
    if pick > 0 and st.button("Open"):
        st.session_state.viewing_session = int(pick)
        st.session_state.qset = None
        st.session_state.screen = "review"
        st.rerun()


def screen_settings() -> None:
    st.title("⚙️ Settings")
    st.markdown(f"**Provider:** `{provider}`")
    st.markdown(f"**Config file:** `{config_path()}`")
    st.caption(
        "To change the provider, edit `houseofmath.config.yaml` or run "
        "`houseofmath init` in your terminal, then refresh this page."
    )

    if st.button("🔌 Test LLM connection"):
        if provider == "none":
            st.info("Provider is `none` — there is nothing to test. Run `houseofmath init` to connect one.")
        else:
            with st.spinner("Pinging the LLM..."):
                try:
                    if not client.is_available():
                        st.error(f"`{provider}` reports it is not available.")
                    else:
                        reply = client.chat(
                            [
                                {"role": "user", "content": "Reply with exactly: pong"},
                            ]
                        )
                        st.success(f"Reply: {reply}")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Failed: {e}")

    st.markdown("---")
    st.markdown("### Question Bank")
    st.caption(f"`{bank}`")
    matrix = _matrix_cached(str(bank))
    if matrix:
        df = pd.DataFrame(matrix).T.reindex(columns=list(LEVELS)).fillna(0).astype(int)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No topics found.")


# ---------- router ----------

SCREENS = {
    "home": screen_home,
    "test": screen_test,
    "review": screen_review,
    "stats": screen_stats,
    "settings": screen_settings,
}

SCREENS.get(st.session_state.screen, screen_home)()
