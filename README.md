# NCBI 物种分类查询系统

从 [NCBI Taxonomy Database](https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/) 构建本地查询服务，支持中文名/拉丁学名/TaxID 搜索，双语（拉丁+中文）分类谱系显示。

## 子目录

| 目录 | 说明 | 独立下载 |
|------|------|----------|
| `taxonomy/` | Python CLI 查询引擎 | 可独立使用 |
| `webui/` | Web 查询界面 | 可独立部署 |
| `.claude/skills/species.md` | `/species` 命令 | 可单独安装为 Claude Code Skill |
| `new_taxdump/` | NCBI 原始数据（需自行下载） | — |

## 快速开始

### 1. 下载 NCBI 数据

从 https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/ 下载 `new_taxdump.zip`，解压到项目根目录下的 `new_taxdump/` 文件夹。

### 2. 一键启动

```bash
# Windows: 双击 start.bat
# Linux/Mac:
./start.sh
```

或手动启动：

```bash
# 构建数据库（首次约 2 分钟）
python -m taxonomy build

# Web 界面
python webui/server.py          # → http://127.0.0.1:8520

# CLI 查询
python -m taxonomy info 9606    # 查询智人
python -m taxonomy search-zh "大肠杆菌"
```

## 只安装 Skill

如果只需要 Claude Code 中的 `/species` 命令：

1. 将 `.claude/skills/species.md` 复制到你项目的 `.claude/skills/` 目录
2. 确保 `taxonomy/` 包和 `taxonomy.db` 在项目根目录
3. 重启 Claude Code 会话

## 只安装 WebUI

如果只需要 Web 查询界面：

1. 复制 `webui/` 目录和 `taxonomy/` 目录到你的项目
2. 确保 `taxonomy.db` 和 `new_taxdump/` 在项目根
3. `python webui/server.py`

## 依赖

纯 Python 3.10+ 标准库，零外部依赖。

## 数据来源

NCBI Taxonomy Database — https://www.ncbi.nlm.nih.gov/taxonomy/
