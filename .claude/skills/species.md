# Species Skill — NCBI 物种分类查询

通过 NCBI Taxonomy 数据库查询物种分类信息，支持中文名、拉丁学名、TaxID 搜索。

## 前置条件

此 skill 需要以下组件在项目中可用：
- `taxonomy/` Python 包（CLI 查询引擎）
- `taxonomy.db` SQLite 数据库（由 `python -m taxonomy build` 生成）
- `new_taxdump/` NCBI 原始 dump 文件（从 NCBI FTP 下载）

## 工作流

当用户调用 `/species` 时：

1. 解析输入：纯数字 → tax_id；含中文 → 搜 extra_zh 词典，不命中则翻译后查拉丁；英文/拉丁 → 直接搜索
2. 调用 `python -m taxonomy` 命令在当前项目根目录下执行
3. 展示结果，数据库缺失的中文名由 Claude 生物学知识补全

## 命令映射

### `/species build`
重建数据库：
```bash
python -m taxonomy build
```

### `/species <名称>` — 按名称查物种
示例: `/species 人类`  `/species E. coli`  `/species 拟南芥`

- 纯数字 → `python -m taxonomy info <id>`
- 含中文 → `python -m taxonomy search-zh "<名称>"`，无结果则翻译后 `python -m taxonomy search "<拉丁名>"`
- 英文/拉丁 → `python -m taxonomy search "<名称>"`
- 取第一个匹配 tax_id，执行 `python -m taxonomy info <tax_id>`
- 多条匹配列出前 5 条供用户选择

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

## 输出处理

- 命令行输出直接展示；缺失中文名由 Claude 生物学知识补全
- 加 `--json` 输出 JSON 格式

## 路径约定

- 命令在项目根目录（含 `taxonomy/` 包 + `taxonomy.db`）执行
- 数据库默认 `./taxonomy.db`，可通过 `--db` 覆盖
- dump 目录默认 `./new_taxdump/`，可通过 `--dump-dir` 覆盖
