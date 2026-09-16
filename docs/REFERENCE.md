# Developer reference / 开发参考

[English overview](../README.md) · [简体中文概览](../README.zh-CN.md)

## Data paths and compatibility

- The recommended `closed_trades` provider reads a private Transactions CSV and writes `docs/data/performance.json` with `metrics` and `daily_cumulative_return_pct` fields. These are the fields consumed by the default dashboard.
- `scripts/update_performance.py --provider manual_entry --csv /private/path/daily_equity.csv` instead computes an indexed total-equity series. Review [the CSV provider](../engine/providers/manual_entry.py) for its input contract. It writes the same output path with a different schema; do not replace the dashboard data without checking frontend compatibility.
- [The Schwab update script](../scripts/daily_schwab_update.py) also produces indexed total-equity data. Raw private history lives at `data/equity_history.json`, not under `docs/`. It must never be committed or publicly hosted.
- The existing Actions workflow starts from a fresh checkout and does not persist that private history between runs. Credentials alone do not establish a usable multi-day history pipeline. Design private persistence and schema-compatible rendering before relying on this path.

## Credential and automation cautions

The existing [workflow](../.github/workflows/daily-update.yml) references `SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`, and `SCHWAB_REFRESH_TOKEN`. It skips updates when any is missing. This documentation does not establish whether repository secrets are configured.

The account owner must obtain authorized Schwab developer access and complete OAuth themselves; [the login helper](../scripts/schwab_login.py) is developer tooling, not a visitor login. Never publish credentials, authorization responses, account identifiers, CSV exports, or raw equity history.

**Review logging before enabling this automation:** the current daily script can print a newly rotated refresh token and can include an unexpected token response in error output. Do not assume CI logs are safe just because configured secrets are masked. The code also expects periodic reauthorization when a refresh token expires. Keep credential setup and sensitive logs out of public issues and screenshots.

None of these optional paths are needed to view the public dashboard. This README refresh does not enable or change any scheduled workflow.

## 数据路径与兼容性

- 推荐的 `closed_trades` provider 读取私有 Transactions CSV，向 `docs/data/performance.json` 写入 `metrics` 和 `daily_cumulative_return_pct`，默认看板使用这些字段。
- `scripts/update_performance.py --provider manual_entry --csv /private/path/daily_equity.csv` 生成的是总净值指数序列。输入格式见 [CSV provider](../engine/providers/manual_entry.py)。它使用相同输出路径，但 schema 不同，替换数据前必须确认前端兼容。
- [Schwab 更新脚本](../scripts/daily_schwab_update.py)同样生成总净值指数。原始私有历史位于 `data/equity_history.json`，不在 `docs/` 下；严禁提交或公开托管。
- 现有 Actions workflow 从全新 checkout 开始，不会在多次运行间持久化私有历史。因此，仅配置凭据还不能形成可用的多日历史流程；需先设计私有存储和兼容的数据展示。

## 凭据与自动化注意事项

现有 [workflow](../.github/workflows/daily-update.yml) 使用 `SCHWAB_APP_KEY`、`SCHWAB_APP_SECRET`、`SCHWAB_REFRESH_TOKEN`，缺少任一项就跳过更新。本文不代表仓库已经配置这些 secrets。

账户所有者需自行取得合法的 Schwab 开发者访问权限并完成 OAuth。[登录辅助脚本](../scripts/schwab_login.py)是开发工具，不是访客登录入口。不得公开凭据、授权响应、账户标识、CSV 导出或原始净值历史。

**启用自动化前请先检查日志：**当前每日更新脚本可能打印轮换后的 refresh token，也可能在异常输出中包含非预期的 token 响应。不能因为 CI 会遮蔽已配置 secrets，就认定所有日志都安全。refresh token 过期时还需重新授权。不要把凭据配置或敏感日志放进公开 issue、截图。

普通访客无需使用这些可选路径。本次 README 更新不会启用或修改任何定时 workflow。
