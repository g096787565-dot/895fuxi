# Streamlit Review App Design

## Goal

Build a clean Streamlit review desk for the 895 hydraulics question bank. The app discovers PDF answer files automatically from `images/简答` and `images/问答`, lets the student draw review batches, reveals PDF notes on demand, and persists mastered questions locally.

## Experience

The first screen is the review workspace, not a landing page. The sidebar contains study controls, progress, and reset actions. The main area shows the current question card, batch progress, answer controls, and a large PDF preview area.

Question text is generated from the discovered file list because the reliable source of truth is the PDF folder structure. A file such as `125-127.pdf` creates question numbers 125, 126, and 127, all linked to the same PDF answer note.

## Core Behaviors

- Discover question ranges from `images/简答` and `images/问答`.
- Exclude mastered questions from random draws.
- Support drawing a batch by type and count.
- Support previous, next, skip, reveal answer, and mark mastered.
- Save progress in `review_progress.json`.
- Show clear warnings when folders or PDFs are missing.
- Keep the UI dense, readable, and usable on Streamlit Community Cloud.

## Validation

Run Python syntax compilation and start Streamlit locally. Confirm the app loads, discovers the PDF-backed question bank, and the Git working tree shows only intended changes.
