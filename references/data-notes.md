# Data Notes

Current bundled dataset:

- Source: public Longbridge profile `3090` (`价值&投资`).
- Refresh timestamp: see `references/data/dataset-summary.md`.
- Covered posts: public activity/topic details from 2020-11-17 through 2026-05-31.
- Stored rows: `activities.jsonl`, `topics.jsonl`, `operations.jsonl`, and `symbol_index.json`.
- Derived views: `symbol_dossiers.json`, `theme_index.json`, `symbol-research-view.md`, and `theme-research-view.md`.

Quality rules:

- `operations.jsonl` is a triage index, not a verified trade ledger.
- Level `A` means the post contains explicit self-operation language; it does not always mean every symbol in a multi-symbol post was operated.
- For symbol-specific conclusions, open the topic text or use `--include-text` before attributing a buy, sell, long call, put, or holding statement.
- `query_longbridge.py --symbol` expands common aliases for 阿里/BABA/09988, 小鹏/XPEV/09868, 腾讯/00700, 美团/03690, 小米/01810, and BRK.B/BRKB.
- One very early activity did not return a public topic payload during the full refresh. Treat count differences between activities and topics as normal unless they grow materially after a refresh.

Useful quick checks:

```bash
python3 scripts/query_longbridge.py --symbol TSLA --level A --limit 20
python3 scripts/query_longbridge.py --keyword 'longcall|long call|put' --limit 30
python3 scripts/query_longbridge.py --source topics --topic-id 40554860 --include-text
python3 scripts/build_research_views.py
python3 scripts/update_and_commit.py --no-push
```
