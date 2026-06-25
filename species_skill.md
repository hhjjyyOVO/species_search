# /species — NCBI 物种分类查询 Skill

> **这是独立下载版 Skill 文件。** 将此文件放入任意项目的 `.claude/skills/` 目录即可启用 `/species` 命令。
>
> 前提：项目中需同时包含 `taxonomy/` Python 包和 `taxonomy.db` 数据库文件。

## 可用命令

### `/species build`
构建/重建 SQLite 数据库（首次使用或 NCBI dump 更新后执行）。

### `/species <名称>`
按名称查询物种。支持中文名、拉丁学名、英文名。

示例：
- `/species 人类` → 查询智人 (Homo sapiens)
- `/species E. coli` → 查询大肠杆菌
- `/species 拟南芥` → 查询 Arabidopsis thaliana

### `/species id <tax_id>`
按 NCBI Taxonomy ID 查询详细信息。

示例：
- `/species id 9606` → 智人
- `/species id 2` → 细菌

### `/species lineage <名称或tax_id>`
显示完整分类谱系（域/界/门/纲/目/科/属/种）。

示例：
- `/species lineage 人类`
- `/species lineage 9606`

### `/species children <名称或tax_id>`
列出某个分类节点下的直接子节点。

示例：
- `/species children 人属`
- `/species children 9605`（Homo 属）

### `/species stats`
显示数据库统计信息。

## 工作流

当用户输入中文名查询时：
1. 先尝试 `python -m taxonomy search-zh "<中文名>"` 在 extra_zh 词典中搜索
2. 若未命中，Claude 将中文名翻译为拉丁学名
3. 使用 `python -m taxonomy search "<拉丁名>"` 在学名表中搜索
4. 获得 tax_id 后调用 `python -m taxonomy info <id>` 显示完整信息
5. 对于数据库中缺失中文翻译的谱系节点，Claude 利用生物学知识补全

## 输出格式

查询结果以**双语格式**呈现：
- 每个分类层级同时显示：**拉丁学名 + 中文翻译**
- 谱系以树形图或表格展示
- 优先使用 NCBI 数据库自带的中文俗名，缺失时由 AI 补充

## 底层调用

所有命令通过 `python -m taxonomy` 执行，数据库默认路径：
- `./taxonomy.db`（项目根目录下）

JSON 模式（程序化使用）：在命令后加 `--json`

```bash
# 构建数据库（项目根目录执行）
python -m taxonomy build

# 查询
python -m taxonomy info <tax_id>
python -m taxonomy search "<keyword>"
python -m taxonomy search-zh "<中文关键词>"
python -m taxonomy lineage <tax_id> --format tree
python -m taxonomy children <tax_id>
python -m taxonomy stats
```

## 安装方法

### 方式一：克隆完整项目
```bash
git clone <repo-url>
cd species
# 下载 NCBI 数据后构建数据库
python -m taxonomy build
```

### 方式二：仅安装 Skill
1. 将本文件 (`species_skill.md`) 复制到你的项目 `.claude/skills/` 目录
2. 将 `taxonomy/` 目录复制到你的项目根目录
3. 下载 NCBI 数据并运行 `python -m taxonomy build`
4. 重启 Claude Code 会话

### 方式三：仅使用 WebUI
1. 复制 `webui/` 和 `taxonomy/` 目录
2. 确保 `taxonomy.db` 在项目根目录
3. `python webui/server.py` → http://127.0.0.1:8520

## 已知物种参考

| 中文名 | 拉丁学名 | Tax ID |
|--------|----------|--------|
| 智人/人类 | Homo sapiens | 9606 |
| 大肠杆菌 | Escherichia coli | 562 |
| 拟南芥 | Arabidopsis thaliana | 3702 |
| 小家鼠 | Mus musculus | 10090 |
| 斑马鱼 | Danio rerio | 7955 |
| 黑腹果蝇 | Drosophila melanogaster | 7227 |
| 酿酒酵母 | Saccharomyces cerevisiae | 4932 |
| 秀丽隐杆线虫 | Caenorhabditis elegans | 6239 |
| 褐家鼠 | Rattus norvegicus | 10116 |
| 水稻 | Oryza sativa | 4530 |
| 玉米 | Zea mays | 4577 |
| 家犬 | Canis lupus familiaris | 9615 |
| 家猫 | Felis catus | 9685 |
| 家牛 | Bos taurus | 9913 |
| 家鸡 | Gallus gallus | 9031 |
| 黑猩猩 | Pan troglodytes | 9598 |
| 金黄色葡萄球菌 | Staphylococcus aureus | 1280 |
| 枯草芽孢杆菌 | Bacillus subtilis | 1423 |
| 铜绿假单胞菌 | Pseudomonas aeruginosa | 287 |
| 结核分枝杆菌 | Mycobacterium tuberculosis | 1773 |
| 幽门螺杆菌 | Helicobacter pylori | 210 |
| 霍乱弧菌 | Vibrio cholerae | 666 |
| 肺炎链球菌 | Streptococcus pneumoniae | 1313 |
| 烟草 | Nicotiana tabacum | 4097 |
| 大豆 | Glycine max | 3847 |
| 普通小麦 | Triticum aestivum | 4565 |
| 恶性疟原虫 | Plasmodium falciparum | 5833 |
| 紫海胆 | Strongylocentrotus purpuratus | 7668 |
| 恒河猴 | Macaca mulatta | 9544 |
