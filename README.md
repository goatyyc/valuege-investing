# ValueGe Investing

语言：中文 | [English](README.en.md)

`valuege-investing` 是一个用于研究长桥用户 `价值&投资` / ValueGe（`member_id=3090`）公开发帖的 Codex Skill 和本地数据集。

它适合用来整理：

- 某只股票的公开操作记录，例如 `MSFT`、`TSLA`、`AAPL`、`BABA`
- longcall、sell put、正股、现金流等策略主题
- 核心持仓、观察仓、安全边际、风控等投资框架
- 可追溯到长桥原帖的公开证据

## 仓库内容

- `SKILL.md`：Codex skill 入口说明
- `references/data/`：长桥公开帖子数据和索引
- `references/symbol-research-view.md`：高频标的研究视图
- `references/theme-research-view.md`：策略主题研究视图
- `scripts/query_longbridge.py`：本地查询脚本
- `scripts/fetch_longbridge.py`：长桥公开数据抓取脚本
- `scripts/build_research_views.py`：重建派生研究视图
- `scripts/update_and_commit.py`：本地增量更新、提交、推送脚本

## 查询数据

```bash
python3 scripts/query_longbridge.py --symbol MSFT --limit 20
python3 scripts/query_longbridge.py --symbol TSLA --level A --limit 20
python3 scripts/query_longbridge.py --keyword 'longcall|long call|put' --limit 30
python3 scripts/query_longbridge.py --symbol 阿里 --limit 20
```

常用证据等级：

- `A`：明确操作，例如买入、卖出、加仓、清仓、longcall、sell put
- `B`：持仓状态，例如核心持仓、正股、长持、非卖品
- `C`：意图或观点，例如看好、观察、等机会、做功课
- `D`：外部信息，例如财报、新闻、他人加仓
- `U`：无法分类或非投资内容

## 手动刷新

```bash
python3 scripts/fetch_longbridge.py --incremental --resume-existing-topics --workers 4 --max-pages 3
python3 scripts/build_research_views.py
```

## 每日本地自动更新

安装 macOS `launchd` 定时任务，默认每天本机时间 `08:30` 运行：

```bash
python3 scripts/install_launchd.py
```

定时任务会运行 `scripts/update_and_commit.py`，流程是：

1. 检查 git 工作区必须干净
2. 增量抓取长桥最新动态
3. 只补新动态对应的 topic 详情
4. 重建标的和主题研究视图
5. 如果数据有变化，自动提交
6. 如果配置了 `origin`，自动推送

日志写入 `logs/`。

安装脚本使用 AppleScript shell wrapper，方便仓库位于 macOS 受保护目录（例如 `Documents`）时也能由定时任务访问。

卸载：

```bash
python3 scripts/uninstall_launchd.py
```

## 证据政策

本仓库只整理长桥公开发帖，不是券商实盘授权记录。回答或引用时应表述为“公开帖子显示”或“他公开写到”，不要把数据集表述成私有实盘持仓证明。

本仓库不提供投资建议。

## 许可证

MIT

