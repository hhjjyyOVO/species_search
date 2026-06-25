# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

NCBI 物种分类查询系统。从 NCBI Taxonomy Database dump 文件构建 SQLite 数据库，支持按学名、中文名、TaxID 查询物种，输出双语（拉丁学名+中文）分类谱系。纯 Python 标准库，零外部依赖。

## 快速启动

```bash
# 一键启动（Windows 双击 start.bat，Linux/Mac 运行 start.sh）
python webui/server.py          # Web 查询界面 → http://127.0.0.1:8520

# CLI 命令行
python -m taxonomy build        # 首次构建数据库（仅需一次）
python -m taxonomy info 9606    # 查询智人
python -m taxonomy search "Homo sapiens"
python -m taxonomy search-zh "大肠杆菌"
python -m taxonomy lineage 9606 --format tree
python -m taxonomy children 9605 --limit 50
python -m taxonomy stats
# 任意命令加 --json 输出 JSON 格式
```

## 架构

```
taxonomy/               # Python 包（纯标准库）
├── builder.py          # TaxonomyBuilder — 流式解析 .dmp → 批量写入 SQLite
├── core.py             # TaxonomyQueryEngine — 递归CTE、谱系、搜索
├── translator.py       # NameTranslator — extra_zh 词典中文名查询
├── formatters.py       # 双语输出格式化
├── cli.py              # argparse CLI（8个子命令）
├── config.py           # 路径/DDL/rank中文映射/EXTRA_ZH词典（98条）
├── models.py           # dataclass
└── utils.py            # dmp解析、CJK检测、进度条

webui/                  # Web 查询界面
├── server.py           # HTTP API 后端（http.server, 端口8520）
└── index.html          # 单页前端（自动检测 file:// 误用）
```

**数据流**: `new_taxdump/*.dmp` → `builder.py` → `taxonomy.db` (~2.7GB) → `core.py`/`webui/server.py` → 用户

**关键设计**:
- `lineage` 表合并 rankedlineage + fullnamelineage + taxidlineage，一次查询获得完整谱系
- `extra_zh` 表手动维护中文名词典（NCBI 不含中文名），`search-zh` 查此表
- 构建时 `PRAGMA journal_mode=OFF; synchronous=OFF` 加速，查询时只读
- Web 界面启动时自动打开浏览器，`start.bat` 自动检测并构建数据库

## 可移植性

- 所有路径使用 `os.path` 相对计算（`PROJECT_ROOT`），无绝对路径硬编码
- `start.bat` 使用 `%~dp0` 定位项目目录
- `start.sh` 使用 `$(dirname "$0")` 定位项目目录
- 数据库和 dump 目录默认在项目根下，CLI 通过 `--db` / `--dump-dir` 覆盖
