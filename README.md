# NCBI 物种分类查询系统

从 NCBI Taxonomy Database 构建本地查询服务，支持中文名/拉丁学名/TaxID 搜索，双语分类谱系显示。纯 Python 标准库，零外部依赖。

## 架构

四个模块可独立下载、独立安装，通过环境变量串联：

```
┌──────────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐
│  taxonomy/   │   │  webui/  │   │  skill/  │   │   astrbot/   │
│  主程序 CLI   │   │ Web 界面  │   │  Claude  │   │  QQ 机器人    │
│              │   │          │   │  /species│   │  /species    │
└──────┬───────┘   └────┬─────┘   └────┬─────┘   └──────┬───────┘
       │                │              │                 │
       └────────────────┴──────────────┴─────────────────┘
                              │
                        taxonomy.db
```

- **taxonomy/** — 主程序 CLI，可安装到任意目录
- **webui/** — Web 查询界面
- **skill/** — Claude Code `/species` 命令
- **astrbot/** — AstrBot QQ 机器人插件

## 模块安装

> 将 `USER/species` 替换为实际 GitHub 仓库路径。`taxonomy/` 可放到任意目录（如 `~/apps/taxonomy/`），其余模块通过路径配置找到它。

### ① 主程序 taxonomy/

**不含 webui、不含 skill，纯 CLI 查询引擎。**

```bash
# 下载
# → https://download-directory.github.io/?url=https://github.com/USER/species/tree/main/taxonomy
# 解压到任意目录，如 ~/apps/taxonomy/

# 下载 NCBI 数据
# → https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/
# → https://ftp.cngb.org/pub/ncbi/taxonomy/          （国内镜像）
# 解压到 new_taxdump/，放在 taxonomy.db 同目录或通过 TAXONOMY_DUMP 指定

# 首次运行自动构建数据库
cd ~/apps/taxonomy
python -m taxonomy info 9606     # 自动构建 taxonomy.db（约 2 分钟）
python -m taxonomy search-zh "大肠杆菌"
```

### ② 安装 WebUI

**依赖 taxonomy/ 主程序。通过环境变量或 CLI 参数指定主程序位置。**

```bash
# 下载 webui/
# → https://download-directory.github.io/?url=https://github.com/USER/species/tree/main/webui
# 解压到任意目录

# 配置路径（二选一）
# 方式 A：环境变量
export TAXONOMY_HOME=~/apps/taxonomy     # taxonomy/ 所在目录
export TAXONOMY_DB=~/data/taxonomy.db    # 数据库路径

# 方式 B：CLI 参数
python server.py --taxonomy-path ~/apps/taxonomy --db ~/data/taxonomy.db

# 启动
python server.py                         # → http://127.0.0.1:8520
```

### ③ 安装 Skill

**依赖 taxonomy/ 主程序。下载 skill 文件放入 `.claude/skills/`，配置路径即可。**

```bash
# 下载 skill/
# → https://download-directory.github.io/?url=https://github.com/USER/species/tree/main/skill
# 将 species.md 放入目标项目的 .claude/skills/

# 配置环境变量（在 ~/.bashrc 或 IDE 设置中）
export TAXONOMY_HOME=~/apps/taxonomy
export TAXONOMY_DB=~/data/taxonomy.db

# 重启 Claude Code，即可使用：
/species 人类
/species id 9606
/species lineage 9606
```

### ④ 安装 AstrBot 插件

**依赖 taxonomy/ 主程序。放入 AstrBot 的 `data/plugins/`，在 QQ/微信/Telegram 中使用。**

```bash
# 下载 astrbot/
# → https://download-directory.github.io/?url=https://github.com/USER/species/tree/main/astrbot/astrbot_plugin_species
# 放入 AstrBot 的 data/plugins/ 目录

# 在 AstrBot WebUI 中配置插件：
#   taxonomy_home: taxonomy/ 包所在目录
#   db_path:       taxonomy.db 路径（可选）
# 或设置环境变量 TAXONOMY_HOME / TAXONOMY_DB
```

| 文件 | 下载方式 |
|------|----------|
| `astrbot_plugin_species/` | [下载 zip](https://download-directory.github.io/?url=https://github.com/USER/species/tree/main/astrbot/astrbot_plugin_species) → 放入 `data/plugins/` |

### ⑤ 全量克隆（一键体验）

```bash
git clone https://github.com/USER/species.git
cd species
# 下载 new_taxdump.zip 解压到 new_taxdump/
./start.sh            # DB 缺失自动构建，之后即开即用
```

## 路径配置参考

所有模块支持以下环境变量（不设置则使用默认相对路径）：

| 变量 | 作用 | 默认值 |
|------|------|--------|
| `TAXONOMY_HOME` | taxonomy/ 包所在目录 | webui 上级目录 / 当前目录 |
| `TAXONOMY_DB` | taxonomy.db 数据库路径 | `./taxonomy.db` |
| `TAXONOMY_DUMP` | new_taxdump/ dump 目录 | `./new_taxdump/` |

WebUI 额外支持 CLI 参数 `--taxonomy-path`、`--db`、`--port`。

## 数据下载

| 来源 | 地址 |
|------|------|
| NCBI 官方 | https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/ |
| CNGB 国内镜像 | https://ftp.cngb.org/pub/ncbi/taxonomy/ |

下载 `new_taxdump.zip`，解压后首次运行自动构建 `taxonomy.db`（约 2.7GB，构建约 2 分钟）。

## 依赖

Python 3.10+，纯标准库。零 pip install。
