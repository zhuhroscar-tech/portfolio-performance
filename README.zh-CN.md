# Portfolio Performance

[![English](https://img.shields.io/badge/English-555555?style=flat)](README.md) [![简体中文](https://img.shields.io/badge/简体中文-555555?style=flat)](README.zh-CN.md)

一个静态投资表现页面，配套 Python 数据处理流程，可把私有券商导出记录转换为百分比统计。默认流程只统计已平仓交易的已实现表现，不公开账户余额、账户标识或单个证券的盈亏。

**普通访客：**直接[打开公开看板](https://zhuhroscar-tech.github.io/portfolio-performance/)即可，无需安装、登录券商或提供 API key。阅读数据时请同时查看计算口径；页面不是投资建议，也不是经过审计的账户报表。

## 默认页面展示什么

- 已实现收益占累计投入资本的百分比。
- 已平仓交易数、胜率、平均持有天数和平均单笔收益率。
- 基于 `docs/data/performance.json` 绘制的累计已实现收益率曲线。

前端是 `docs/index.html` 中的原生 HTML 和 SVG，无应用服务器、数据库或前端构建步骤。

## 开发者快速上手

建议使用 CI 所用的 Python 3.12。默认处理流程仅依赖标准库，测试需要 pytest。

```bash
git clone https://github.com/zhuhroscar-tech/portfolio-performance.git
cd portfolio-performance
python3 -m http.server 8000 --bind 127.0.0.1 --directory docs
```

打开 `http://127.0.0.1:8000`。若要更新**自己的 fork**，停止预览后运行：

```bash
python3 scripts/update_performance.py --provider closed_trades --csv /private/path/transactions.csv
```

输入为 Schwab 风格的 Transactions CSV，包含 Date、Action、Symbol、Quantity、Price、Fees & Comm、Amount 列。检查生成的 JSON 后，**只提交** `docs/data/performance.json`。CSV、原始历史、凭据及账户信息必须保密；`.gitignore` 只是防护措施，不能代替隐私检查。

## 计算口径与限制

已平仓交易按持仓从零到零的完整往返计算，采用 FIFO 匹配。同日成交顺序通过反转导出文件的倒序行推断，不是券商确认的执行时间顺序。投入资本取正值 `MoneyLink Transfer` 记录之和；导出不完整会影响分母。

未平仓持仓、股息、利息、税费及账户级融资成本均不计入。这既不是盯市账户表现，也不是时间加权或年化收益率。公开内容仅含百分比、计数、时长、日期及说明元数据，不含资金金额或账号。

## 可选开发路径

`manual_entry` 和 Schwab API 路径输出的是**另一套净值指数 schema**，不是默认的已平仓统计，不能直接替换本页面的数据。现有每日 workflow 在缺少凭据时跳过更新；它的存在不代表真实券商连接已配置。

使用自动化前，请阅读[开发参考](docs/REFERENCE.md)，了解 schema 兼容性、私有历史持久化，以及凭据和日志风险。普通访客不需要运行处理流程或提供凭据。

## 测试

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
python -m pytest tests/ -v
```

[发布历史](CHANGELOG.md) · [MIT 许可证](LICENSE)。
