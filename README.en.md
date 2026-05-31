# ValueGe Investing

Language: [中文](README.md) | English

`valuege-investing` is a Codex skill and local dataset for researching public Longbridge posts by `价值&投资` / ValueGe (`member_id=3090`).

It helps summarize:

- public operation timelines for symbols such as `MSFT`, `TSLA`, `AAPL`, and `BABA`
- strategy themes such as long calls, sell puts, common shares, and cashflow
- investing-framework themes such as core holdings, watch positions, margin of safety, and risk control
- evidence that links back to original Longbridge topic pages

## Repository Contents

- `SKILL.md`: Codex skill entrypoint
- `references/data/`: public Longbridge post data and indexes
- `references/symbol-research-view.md`: compact symbol research view
- `references/theme-research-view.md`: compact strategy-theme view
- `scripts/query_longbridge.py`: local query helper
- `scripts/fetch_longbridge.py`: public Longbridge fetcher
- `scripts/build_research_views.py`: derived research-view builder
- `scripts/update_and_commit.py`: local incremental update, commit, and push helper

## Query The Dataset

```bash
python3 scripts/query_longbridge.py --symbol MSFT --limit 20
python3 scripts/query_longbridge.py --symbol TSLA --level A --limit 20
python3 scripts/query_longbridge.py --keyword 'longcall|long call|put' --limit 30
python3 scripts/query_longbridge.py --symbol 阿里 --limit 20
```

Evidence levels:

- `A`: explicit operation, such as buy, sell, add, trim, clear, long call, or sell put
- `B`: holding status, such as core holding, common shares, long hold, or non-sellable
- `C`: intent or thesis, such as bullish view, watchlist, wait-for-opportunity, or research
- `D`: external information, such as earnings, news, or another investor's activity
- `U`: unclassified or non-investment content

## Manual Refresh

```bash
python3 scripts/fetch_longbridge.py --incremental --resume-existing-topics --workers 4 --max-pages 3
python3 scripts/build_research_views.py
```

## Daily Local Auto Update

Install a macOS `launchd` job that runs every day at 08:30 local time:

```bash
python3 scripts/install_launchd.py
```

The job runs `scripts/update_and_commit.py`, which:

1. refuses to run if the git worktree is dirty
2. fetches incremental Longbridge activities
3. fetches missing topic details for new activities
4. rebuilds derived symbol and theme views
5. commits generated data changes when there is a diff
6. pushes to `origin` when configured

Logs are written to `logs/`.

The installer uses an AppleScript shell wrapper so the job can run even when the repository lives under macOS-protected folders such as `Documents`.

Uninstall:

```bash
python3 scripts/uninstall_launchd.py
```

## Evidence Policy

This repository summarizes public Longbridge posts only. It is not a verified brokerage ledger. Phrase conclusions as "public posts show" or "he publicly wrote"; do not present this dataset as private trade-record authorization.

This repository does not provide investment advice.

## License

MIT

