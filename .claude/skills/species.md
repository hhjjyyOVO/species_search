# Species Skill — NCBI 物种分类查询

通过 NCBI Taxonomy 数据库查询物种分类信息，支持中文名、拉丁学名、TaxID 搜索。

## 前置条件

- `taxonomy/` Python 包
- `new_taxdump/` NCBI dump（[NCBI](https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/) / [CNGB镜像](https://ftp.cngb.org/pub/ncbi/taxonomy/)）
- `taxonomy.db` 首次运行自动构建（约 2 分钟）

## 工作流

0. 如设置了 `TAXONOMY_HOME` 则先 `cd $TAXONOMY_HOME`，确保 Python 能找到 taxonomy 包
1. 解析：纯数 → tax_id；中文 → 先 extra_zh 再翻译；拉丁/英文 → 直接搜索
2. 缺失中文名由 Claude 补全，`--json` 输出 JSON

## 命令映射

> 如设置了 `TAXONOMY_HOME`，命令在该目录执行。`TAXONOMY_DB` / `TAXONOMY_DUMP` 通过环境变量自动生效。

### `/species build`
```bash
python -m taxonomy build
```

### `/species <名称>`
- 纯数字 → `python -m taxonomy info <id>`
- 含中文 → `python -m taxonomy search-zh "<名称>"`，无结果译后 `python -m taxonomy search "<拉丁名>"`
- 英文/拉丁 → `python -m taxonomy search "<名称>"`
- 取第一个匹配 `python -m taxonomy info <tax_id>`；多条列出前 5 条

### `/species id <tax_id>`
```bash
python -m taxonomy info <tax_id>
```

### `/species lineage <名称或id>`
```bash
python -m taxonomy lineage <tax_id> --format tree
```

### `/species children <名称或id>`
```bash
python -m taxonomy children <tax_id> --limit 50
```

### `/species stats`
```bash
python -m taxonomy stats
```

## 路径

- 默认：项目根目录，`./taxonomy.db`，`--db` 覆盖
- 模块化：设置 `TAXONOMY_HOME` / `TAXONOMY_DB` / `TAXONOMY_DUMP` 环境变量
- 未设置时使用默认相对路径（全量克隆零配置）
