# Streamlit Review App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the corrupted Streamlit prototype with a polished PDF-driven review app.

**Architecture:** Keep the app in `app.py` for Streamlit Cloud simplicity. Split the file internally into discovery, persistence, session state, UI helpers, and rendering sections.

**Tech Stack:** Python, Streamlit, local JSON persistence, base64 PDF iframe rendering.

---

### Task 1: Rewrite Streamlit App

**Files:**
- Modify: `app.py`
- Persisted runtime file: `review_progress.json`

- [ ] Replace the corrupted manual question list with automatic PDF discovery from `images/简答` and `images/问答`.
- [ ] Add resilient JSON load/save helpers for mastered IDs and check-in counts.
- [ ] Add sidebar controls for question type, draw count, progress, and reset actions.
- [ ] Add main question card with previous, next, reveal answer, skip, and mark-mastered actions.
- [ ] Add PDF iframe rendering and missing-file warnings.

### Task 2: Verify Locally

**Files:**
- Check: `app.py`
- Check: `images/简答`
- Check: `images/问答`

- [ ] Run `python -m py_compile app.py`.
- [ ] Start `streamlit run app.py` and confirm the server launches.
- [ ] Check `git status --short` for intended changes.

### Task 3: Commit And Push

**Files:**
- Commit: `app.py`
- Commit: `docs/superpowers/specs/2026-06-15-streamlit-review-app-design.md`
- Commit: `docs/superpowers/plans/2026-06-15-streamlit-review-app.md`

- [ ] Stage intended files.
- [ ] Commit with `Improve Streamlit review app`.
- [ ] Push `main` to `origin`.
