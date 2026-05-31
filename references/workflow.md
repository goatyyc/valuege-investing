# Workflow

## Refresh Data

Run from the skill directory:

```bash
python3 scripts/fetch_longbridge.py
```

Useful options:

```bash
python3 scripts/fetch_longbridge.py --max-pages 2 --max-topics 20
python3 scripts/fetch_longbridge.py --incremental --resume-existing-topics --workers 4 --max-pages 3
python3 scripts/fetch_longbridge.py --activities-only
python3 scripts/fetch_longbridge.py --sleep 0.25
python3 scripts/fetch_longbridge.py --use-existing-activities --resume-existing-topics --workers 4 --save-every 50
python3 scripts/build_research_views.py
```

Generated files:

- `references/data/profile.json`: profile and topic counts.
- `references/data/activities.jsonl`: normalized activity stream.
- `references/data/topics.jsonl`: normalized topic details.
- `references/data/operations.jsonl`: A/B/C evidence rows for operations, holdings, and intent.
- `references/data/symbol_index.json`: symbol-centric index.
- `references/data/symbol_dossiers.json`: top-symbol evidence snapshots.
- `references/data/theme_index.json`: recurring strategy theme matches.
- `references/data/dataset-summary.md`: refresh timestamp, counts, date range, and evidence-level distribution.
- `references/symbol-research-view.md`: compact top-symbol Markdown view.
- `references/theme-research-view.md`: compact strategy-theme Markdown view.

## Query Data

Use the query helper instead of loading full JSONL files into context.

```bash
python3 scripts/query_longbridge.py --symbol TSLA --limit 20
python3 scripts/query_longbridge.py --symbol AMZN --level A --limit 20
python3 scripts/query_longbridge.py --keyword 'longcall|long call|put' --limit 30
python3 scripts/query_longbridge.py --source topics --keyword '王子落难|安全边际' --limit 20
python3 scripts/query_longbridge.py --source topics --topic-id 40554860 --include-text
python3 scripts/query_longbridge.py --symbol TSLA --since 2026-01-01 --until 2026-05-31
python3 scripts/query_longbridge.py --symbol 阿里 --limit 20
python3 scripts/query_longbridge.py --symbol BABA --format jsonl --limit 20
```

For a deeper answer, inspect the matching topic links and only then summarize.

## Scheduled Updates

Use `scripts/update_and_commit.py` for local automation. It expects a clean git worktree, runs incremental fetch, rebuilds research views, stages only generated data/view files, commits changes, and pushes to `origin` unless disabled.

```bash
python3 scripts/update_and_commit.py
VALUEGE_AUTO_PUSH=0 python3 scripts/update_and_commit.py
python3 scripts/update_and_commit.py --no-push
```

On macOS, install a daily launchd job:

```bash
python3 scripts/install_launchd.py --hour 8 --minute 30
```

Logs are written to `logs/`. Remove the job with:

```bash
python3 scripts/uninstall_launchd.py
```

## Answer Shape

For "某只股票怎么看":

1. Current public stance: summarize the latest A/B/C evidence.
2. Operation timeline: list only level A rows first.
3. Holding/thesis: add level B/C rows.
4. Caveats: mention public-post-only limitation and no private trading record.

For "整理操作":

1. Filter `operations.jsonl` by level `A`.
2. Group by symbol and date.
3. Distinguish common shares from long calls and puts.
4. Mark uncertain rows as "需要人工复核".

For "投资框架":

1. Search the full topic set for recurring thesis terms.
2. Use multiple source links, not one isolated post.
3. Separate durable principles from one-off comments.
