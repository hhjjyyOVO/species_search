# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

NCBI 物种分类查询系统。从 NCBI Taxonomy Database dump 文件构建 SQLite 数据库，支持按学名、中文名、TaxID 查询物种，输出双语（拉丁学名+中文）分类谱系。纯 Python 标准库，零外部依赖。

## 快速启动

```bash
# 首次使用：下载 new_taxdump.zip 解压到 new_taxdump/
# 来源: https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/
# 镜像: https://ftp.cngb.org/pub/ncbi/taxonomy/

# 一键启动（DB 缺失自动构建，约 2 分钟）
python webui/server.py          # Web 查询界面 → http://127.0.0.1:8520

# CLI 命令行（DB 缺失自动构建）
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
taxonomy/               # 主程序 CLI（纯标准库）
├── builder.py          # TaxonomyBuilder — 流式解析 .dmp → 批量写入 SQLite
├── core.py             # TaxonomyQueryEngine — 递归CTE、谱系、搜索
├── translator.py       # NameTranslator — extra_zh 词典中文名查询
├── formatters.py       # 双语输出格式化
├── cli.py              # argparse CLI（8个子命令）
├── config.py           # 路径/DDL/rank中文映射/EXTRA_ZH词典 + 环境变量
├── models.py           # dataclass
└── utils.py            # dmp解析、CJK检测、进度条

webui/                  # Web 查询界面（独立模块）
├── server.py           # HTTP API + --db --taxonomy-path 参数
└── index.html          # 单页前端

skill/                  # Claude Code Skill（独立模块）
└── species.md          # 放入 .claude/skills/ 即可用

astrbot/                # AstrBot QQ 机器人插件（独立模块）
└── astrbot_plugin_species/
    ├── main.py         # Star 插件入口 — 4 个命令组
    ├── metadata.yaml   # 插件元数据
    └── _conf_schema.json  # WebUI 配置表单
```

**数据流**: `new_taxdump/*.dmp` → `builder.py` → `taxonomy.db` (~2.7GB) → `core.py`/`server.py`/`main.py` → 用户

**关键设计**:
- `lineage` 表合并 rankedlineage + fullnamelineage + taxidlineage，一次查询获得完整谱系
- `extra_zh` 表手动维护中文名词典，`search-zh` 查此表
- 构建时 `PRAGMA journal_mode=OFF; synchronous=OFF` 加速，查询时只读
- 首次运行 DB 缺失时自动构建，无需手动 `build`

## 模块化路径

三模块可独立安装到不同目录，通过环境变量串联：

| 变量 | 作用 |
|------|------|
| `TAXONOMY_HOME` | taxonomy/ 包所在目录 |
| `TAXONOMY_DB` | taxonomy.db 数据库路径 |
| `TAXONOMY_DUMP` | new_taxdump/ dump 目录 |

未设置时自动使用默认相对路径，全量克隆场景零配置。WebUI 额外支持 `--taxonomy-path` `--db` `--port` CLI 参数。
