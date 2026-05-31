---
name: valuege-investing
description: Analyze ValueGe / 价值&投资 public Longbridge posts, operations, holdings, and investing theses. Use when asked to query or summarize 长桥价值哥, ValueGe, member 3090, his public stock operations, long call or put activity, holdings, symbol-specific views, or investment framework.
---

# ValueGe Investing

## Core Rule

Treat this as a public-source research skill, not a trading-advice skill. Never imply access to private brokerage records. Longbridge trade-record authorization is not public, so all claims must be phrased as public-post evidence.

## Resources

- Read `references/source-policy.md` when producing user-facing conclusions.
- Read `references/workflow.md` when refreshing or querying the dataset.
- Read `references/data-notes.md` when the user asks about coverage, counts, or data quality.
- Read `references/symbol-research-view.md` for high-frequency symbols and symbol-level starting points.
- Read `references/theme-research-view.md` for recurring strategy themes such as longcall, put, core holdings, cashflow, and safety margin.
- Use `scripts/query_longbridge.py` for symbol, keyword, or evidence-level lookups.
- Use `scripts/fetch_longbridge.py` to refresh the public Longbridge dataset.
- Use `scripts/build_research_views.py` after refreshes to rebuild derived symbol and theme views.
- Use `scripts/update_and_commit.py` for scheduled local incremental refresh, generated-file commit, and optional push.

## Evidence Discipline

Use the bundled evidence levels:

- `A`: explicit operation.
- `B`: stated holding status.
- `C`: intent, watchlist, or thesis.
- `D`: external information only.
- `U`: unclassified.

Lead with level `A` rows when the user asks about operations. Use level `B` and `C` rows for stance and framework. Do not mix level `D` external information into "his operation" unless he explicitly says he acted on it.

Classification is heuristic. Multi-symbol posts can contain one explicit operation plus several contextual tickers; inspect the topic text before attributing the operation to every symbol in that row.

## Query Examples

```bash
python3 scripts/query_longbridge.py --symbol TSLA --limit 20
python3 scripts/query_longbridge.py --symbol BRK.B --level A --limit 20
python3 scripts/query_longbridge.py --keyword 'longcall|long call|put' --limit 30
python3 scripts/query_longbridge.py --topic-id 40554860 --source topics --include-text
python3 scripts/query_longbridge.py --symbol AAPL --since 2026-01-01 --limit 20
python3 scripts/query_longbridge.py --symbol 阿里 --limit 20
python3 scripts/query_longbridge.py --symbol BABA --format jsonl --limit 20
python3 scripts/query_longbridge.py --source topics --keyword '核心持仓|非卖品|和时间做朋友' --limit 30
python3 scripts/build_research_views.py
python3 scripts/update_and_commit.py
```

## Response Pattern

When answering a symbol-specific question:

1. State the data scope and latest refresh date if available.
2. Summarize explicit operations first.
3. Summarize stated holding status and thesis second.
4. Cite Longbridge topic URLs for concrete claims.
5. Close with limitations: public posts only, not verified private trades, not investment advice.

When answering a framework question:

1. Use multiple posts across time.
2. Group principles, for example: core holdings, option cashflow, defensive buffer, small-growth risk control, product-use conviction.
3. Avoid copying long post text; paraphrase and link.
4. Use `references/theme-research-view.md` first, then drill into topic text for key examples.
