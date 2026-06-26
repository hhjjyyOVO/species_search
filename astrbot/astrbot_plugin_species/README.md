# AstrBot 物种查询插件

在 QQ / Telegram / 微信 中查询 NCBI 物种分类数据库。

## 安装

### 依赖

- 本插件（放入 AstrBot 的 `data/plugins/` 目录）
- [taxonomy/](https://github.com/USER/species/tree/main/taxonomy) Python 包（NCBI 分类查询引擎）
- `taxonomy.db` 数据库（首次运行自动构建，约 2.7GB）

### 步骤

1. 下载本插件到 AstrBot 的 `data/plugins/astrbot_plugin_species/`
2. 下载 taxonomy/ 包到任意目录（如 `~/apps/taxonomy/`）
3. 下载 NCBI dump 数据并解压到 `new_taxdump/`
4. 在 AstrBot WebUI 中配置插件：
   - `taxonomy_home`: taxonomy/ 包所在目录
   - `db_path`: taxonomy.db 路径（可选，留空自动查找）
5. 重启插件

或设置环境变量（无需配置插件）：
```bash
export TAXONOMY_HOME=~/apps/species
export TAXONOMY_DB=~/data/taxonomy.db
```

## 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/species <名称>` | 按名称或 TaxID 查询 | `/species 人类` |
| `/species lineage <名称>` | 完整分类谱系 | `/species lineage 9606` |
| `/species children <名称>` | 直接子节点 | `/species children 人属` |
| `/species stats` | 数据库统计 | `/species stats` |

## 数据来源

NCBI Taxonomy Database — https://www.ncbi.nlm.nih.gov/taxonomy/
