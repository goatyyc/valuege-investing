# ValueGe Investing

Codex skill and public Longbridge dataset for researching `价值&投资` / ValueGe (`member_id=3090`).

This repository contains:

- a Codex skill (`SKILL.md`) for answering ValueGe operation, holding, and investing-framework questions
- public Longbridge post data under `references/data/`
- query and refresh scripts under `scripts/`
- an optional local macOS daily updater that commits and pushes incremental dataset changes

## Use The Dataset

```bash
python3 scripts/query_longbridge.py --symbol MSFT --limit 20
python3 scripts/query_longbridge.py --symbol TSLA --level A --limit 20
python3 scripts/query_longbridge.py --keyword 'longcall|long call|put' --limit 30
python3 scripts/query_longbridge.py --symbol 阿里 --limit 20
```

## Refresh Manually

```bash
python3 scripts/fetch_longbridge.py --incremental --resume-existing-topics --workers 4 --max-pages 3
python3 scripts/build_research_views.py
```

## Daily Local Auto Update

Install a macOS launchd job that runs every day at 08:30 local time:

```bash
python3 scripts/install_launchd.py
```

The job runs `scripts/update_and_commit.py`, which:

1. refuses to run if the git worktree is dirty
2. fetches incremental Longbridge activities
3. fetches missing topic details for new activities
4. rebuilds derived research views
5. commits generated data changes
6. pushes to `origin` when available

Logs are written to `logs/`.

Uninstall:

```bash
python3 scripts/uninstall_launchd.py
```

## Evidence Policy

This is public-post research, not a verified brokerage ledger. Phrase conclusions as "public posts show" or "he publicly wrote". Do not present the dataset as private trade-record authorization.

## License

MIT

