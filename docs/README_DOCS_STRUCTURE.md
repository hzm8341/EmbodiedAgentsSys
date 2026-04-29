# Docs Structure Guide

## Purpose
This document defines what belongs in each docs folder and how to archive old material.

## Top-level docs policy (`docs/*.md`)
Only keep actively used, user-facing canonical docs at root:
- `index.md`
- `intro.md`
- `installation.md`
- `quickstart.md`
- `API_REFERENCE.md`
- `USER_GUIDE.md`
- `DEVELOPER_GUIDE.md`
- `ARCHITECTURE.md`
- `README.zh.md`
- `README.ja.md`
- `TEST_MANUAL.md`
- `README_DOCS_STRUCTURE.md`

Everything else should be moved out of root.

## Folder responsibilities
- `docs/api/`: API sub-docs and protocol-specific references.
- `docs/basics/`: conceptual building blocks and core abstractions.
- `docs/examples/`: runnable recipes and usage examples.
- `docs/guides/`: operational guides (deployment, workflows, etc.).
- `docs/tutorials/`: step-by-step deep-dive tutorials.
- `docs/plans/`: active historical implementation plans/design records.
- `docs/summaries/`: milestone and weekly summary reports.
- `docs/superpowers/specs/`: design specs created by superpowers workflows.
- `docs/superpowers/plans/`: implementation plans created by superpowers workflows.
- `docs/archived/`: archived/legacy materials not part of active primary docs.

## Archival rules
1. If a document is duplicated elsewhere with same content, keep one canonical copy and remove duplicates.
2. If a document is no longer part of active docs navigation, move it under `docs/archived/`.
3. Keep filenames stable where possible to preserve history.
4. Prefer moving to `docs/archived/legacy-root/` for files previously placed in `docs/` root.

## Contribution rules
1. New plans should go to `docs/superpowers/plans/` (or `docs/plans/` when not using superpowers process).
2. New design specs should go to `docs/superpowers/specs/`.
3. Avoid adding new miscellaneous files directly to `docs/` root.
