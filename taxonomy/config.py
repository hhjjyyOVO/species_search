"""NCBI Taxonomy 项目配置：路径常量、SQL DDL、中文 rank 名映射"""

import os

# ── 路径常量 ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DUMP_DIR = os.path.join(PROJECT_ROOT, "new_taxdump")
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "taxonomy.db")

SCHEMA_VERSION = 2

# ── 文件格式常量 ──────────────────────────────────────────
FIELD_SEP = "\t|\t"       # 字段分隔符
RECORD_SEP = "\t|\n"      # 记录终止符

# ── 名称为中文的 name_class 类型 ──────────────────────────
ZH_NAME_CLASSES = {"common name", "genbank common name", "blast name", "equivalent name"}

# ── 中文 rank 名映射 ─────────────────────────────────────
RANK_CN = {
    "domain":        "域",
    "superkingdom":  "域",
    "realm":         "界",
    "kingdom":       "界",
    "subkingdom":    "亚界",
    "superphylum":   "总门",
    "phylum":        "门",
    "subphylum":     "亚门",
    "superclass":    "总纲",
    "class":         "纲",
    "subclass":      "亚纲",
    "infraclass":    "下纲",
    "cohort":        "群",
    "subcohort":     "亚群",
    "superorder":    "总目",
    "order":         "目",
    "suborder":      "亚目",
    "infraorder":    "下目",
    "parvorder":     "小目",
    "superfamily":   "总科",
    "family":        "科",
    "subfamily":     "亚科",
    "tribe":         "族",
    "subtribe":      "亚族",
    "genus":         "属",
    "subgenus":      "亚属",
    "section":       "组",
    "subsection":    "亚组",
    "series":        "系",
    "subseries":     "亚系",
    "species group":  "种组",
    "species subgroup": "种亚组",
    "species":       "种",
    "subspecies":    "亚种",
    "varietas":      "变种",
    "forma":         "型",
    "no rank":       "未定级",
    "clade":         "支序",
    "biotype":       "生物型",
    "serotype":      "血清型",
    "genotype":      "基因型",
    "isolate":       "分离株",
    "morph":         "形态型",
    "strain":        "菌株",
}

# ── 常见中文俗名词典（数据库查询不到时用） ───────────────
# key = 拉丁学名(全小写), value = 中文名
EXTRA_ZH = {
    "cellular organisms":    "细胞生物",
    "eukaryota":             "真核生物",
    "archaea":               "古菌",
    "bacteria":              "细菌",
    "metazoa":               "后生动物",
    "viridiplantae":         "绿色植物",
    "fungi":                 "真菌",
    "chordata":              "脊索动物门",
    "vertebrata":            "脊椎动物",
    "mammalia":              "哺乳纲",
    "primates":              "灵长目",
    "hominidae":             "人科",
    "homo":                  "人属",
    "homo sapiens":          "智人",
    "escherichia coli":      "大肠杆菌",
    "arabidopsis thaliana":  "拟南芥",
    "mus musculus":          "小家鼠",
    "danio rerio":           "斑马鱼",
    "drosophila melanogaster": "黑腹果蝇",
    "saccharomyces cerevisiae": "酿酒酵母",
    "caenorhabditis elegans": "秀丽隐杆线虫",
    "rattus norvegicus":     "褐家鼠",
    "oryza sativa":          "水稻",
    "zea mays":              "玉米",
    "canis lupus familiaris": "家犬",
    "felis catus":           "家猫",
    "bos taurus":            "家牛",
    "sus scrofa":            "野猪/家猪",
    "gallus gallus":         "原鸡/家鸡",
    "pan troglodytes":       "黑猩猩",
    "nicotiana tabacum":     "烟草",
    "macaca mulatta":        "猕猴/恒河猴",
    "salmonella enterica":   "肠道沙门氏菌",
    "staphylococcus aureus": "金黄色葡萄球菌/金葡菌",
    "bacillus subtilis":     "枯草芽孢杆菌",
    "pseudomonas aeruginosa": "铜绿假单胞菌",
    "mycobacterium tuberculosis": "结核分枝杆菌/结核杆菌",
    "yersinia pestis":       "鼠疫耶尔森菌/鼠疫杆菌",
    "vibrio cholerae":       "霍乱弧菌",
    "helicobacter pylori":   "幽门螺杆菌",
    "streptococcus pneumoniae": "肺炎链球菌",
    "listeria monocytogenes": "单核细胞增生李斯特菌",
    "bacillus anthracis":    "炭疽芽孢杆菌/炭疽杆菌",
    "solanum lycopersicum":  "番茄/西红柿",
    "canis lupus":           "狼",
    "equus caballus":        "家马",
    "ovis aries":            "绵羊",
    "capra hircus":          "山羊",
    "anopheles gambiae":     "冈比亚按蚊",
    "apis mellifera":        "西方蜜蜂",
    "bombyx mori":           "家蚕",
    "xenopus tropicalis":    "热带爪蟾",
    "takifugu rubripes":     "红鳍东方鲀/河豚",
    "macaca fascicularis":   "食蟹猴/长尾猕猴",
    "papio anubis":          "橄榄狒狒",
    "canis latrans":         "郊狼",
    "vulpes vulpes":         "赤狐",
    "ailuropoda melanoleuca": "大熊猫",
    "loxodonta africana":    "非洲象",
    "balaenoptera musculus": "蓝鲸",
    "panthera tigris":       "虎",
    "panthera leo":          "狮",
    "equus asinus":          "驴",
    "camelus dromedarius":   "单峰驼",
    "struthio camelus":      "鸵鸟",
    "gallus gallus domesticus": "家鸡",
    "anas platyrhynchos":    "绿头鸭/家鸭",
    "columba livia":         "原鸽/家鸽",
    "oncorhynchus mykiss":   "虹鳟",
    "salmo salar":           "大西洋鲑",
    "cyprinus carpio":       "鲤鱼",
    "ictalurus punctatus":   "斑点叉尾鮰",
    "penaeus vannamei":      "凡纳滨对虾/南美白对虾",
    "crassostrea gigas":     "长牡蛎/太平洋牡蛎",
    "helix pomatia":         "罗马蜗牛",
    "lumbricus terrestris":  "普通蚯蚓",
    "caenorhabditis briggsae": "布里格氏线虫",
    "schistosoma mansoni":   "曼氏血吸虫",
    "echinococcus granulosus": "细粒棘球绦虫",
    "trichinella spiralis":  "旋毛虫",
    "brugia malayi":         "马来丝虫",
    "ascaris suum":          "猪蛔虫",
    "strongylocentrotus purpuratus": "紫海胆",
    "ciona intestinalis":    "玻璃海鞘",
    "ciona savignyi":        "萨氏海鞘",
    "branchiostoma floridae": "佛罗里达文昌鱼",
    "petromyzon marinus":    "海七鳃鳗",
    "callorhinchus milii":   "象鲨/澳洲鬼鲨",
    "lepisosteus oculatus":  "眼斑雀鳝",
    "oreochromis niloticus": "尼罗罗非鱼",
    "gasterosteus aculeatus": "三刺鱼",
    "xiphophorus maculatus": "花斑剑尾鱼",
    "nothobranchius furzeri": "弗氏假鳃鳉",
    "latimeria chalumnae":   "西印度洋矛尾鱼/腔棘鱼",
    "ornithorhynchus anatinus": "鸭嘴兽",
    "monodelphis domestica": "短尾负鼠",
    "macropus eugenii":      "尤金袋鼠",
    "sarcophilus harrisii":  "袋獾/塔斯马尼亚恶魔",
}

# ── SQL DDL ──────────────────────────────────────────────
DDL = {
    "nodes": """
        CREATE TABLE IF NOT EXISTS nodes (
            tax_id              INTEGER PRIMARY KEY,
            parent_tax_id       INTEGER NOT NULL,
            rank                TEXT    NOT NULL,
            division_id         INTEGER,
            genetic_code_id     INTEGER,
            mito_GC_id          INTEGER,
            genbank_hidden_flag INTEGER DEFAULT 0,
            subtree_hidden_flag INTEGER DEFAULT 0,
            comments            TEXT,
            specified_species   INTEGER DEFAULT 0
        )
    """,

    "names": """
        CREATE TABLE IF NOT EXISTS names (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tax_id      INTEGER NOT NULL,
            name_txt    TEXT    NOT NULL,
            unique_name TEXT,
            name_class  TEXT    NOT NULL
        )
    """,

    "lineage": """
        CREATE TABLE IF NOT EXISTS lineage (
            tax_id        INTEGER PRIMARY KEY,
            tax_name      TEXT,
            species       TEXT,
            genus         TEXT,
            family        TEXT,
            "order"       TEXT,
            class         TEXT,
            phylum        TEXT,
            kingdom       TEXT,
            domain        TEXT,
            taxid_lineage TEXT,
            name_lineage  TEXT
        )
    """,

    "zh_names": """
        CREATE TABLE IF NOT EXISTS zh_names (
            tax_id  INTEGER NOT NULL,
            zh_name TEXT    NOT NULL,
            PRIMARY KEY (tax_id, zh_name)
        )
    """,

    "extra_zh": """
        CREATE TABLE IF NOT EXISTS extra_zh (
            name_key TEXT PRIMARY KEY,
            zh_name  TEXT NOT NULL
        )
    """,

    "divisions": """
        CREATE TABLE IF NOT EXISTS divisions (
            division_id   INTEGER PRIMARY KEY,
            division_code TEXT,
            division_name TEXT
        )
    """,

    "genetic_codes": """
        CREATE TABLE IF NOT EXISTS genetic_codes (
            genetic_code_id  INTEGER PRIMARY KEY,
            abbreviation     TEXT,
            name             TEXT,
            translation_table TEXT,
            start_codons     TEXT
        )
    """,

    "merged_ids": """
        CREATE TABLE IF NOT EXISTS merged_ids (
            old_tax_id INTEGER PRIMARY KEY,
            new_tax_id INTEGER NOT NULL
        )
    """,

    "deleted_ids": """
        CREATE TABLE IF NOT EXISTS deleted_ids (
            tax_id INTEGER PRIMARY KEY
        )
    """,

    "host_info": """
        CREATE TABLE IF NOT EXISTS host_info (
            tax_id          INTEGER,
            potential_hosts TEXT
        )
    """,

    "type_material": """
        CREATE TABLE IF NOT EXISTS type_material (
            tax_id     INTEGER,
            tax_name   TEXT,
            type       TEXT,
            identifier TEXT
        )
    """,

    "type_of_type": """
        CREATE TABLE IF NOT EXISTS type_of_type (
            type_name    TEXT,
            nomenclature TEXT,
            description  TEXT
        )
    """,

    "meta": """
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """,
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_tax_id)",
    "CREATE INDEX IF NOT EXISTS idx_nodes_rank   ON nodes(rank)",
    "CREATE INDEX IF NOT EXISTS idx_names_taxid  ON names(tax_id)",
    "CREATE INDEX IF NOT EXISTS idx_names_text   ON names(name_txt COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_names_class  ON names(name_class)",
    "CREATE INDEX IF NOT EXISTS idx_zh_taxid     ON zh_names(tax_id)",
    "CREATE INDEX IF NOT EXISTS idx_zh_name      ON zh_names(zh_name COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_lineage_genus   ON lineage(genus)",
    "CREATE INDEX IF NOT EXISTS idx_lineage_family  ON lineage(family)",
    "CREATE INDEX IF NOT EXISTS idx_lineage_order   ON lineage(\"order\")",
    "CREATE INDEX IF NOT EXISTS idx_lineage_species ON lineage(species)",
    "CREATE INDEX IF NOT EXISTS idx_lineage_class   ON lineage(class)",
    "CREATE INDEX IF NOT EXISTS idx_lineage_phylum  ON lineage(phylum)",
    "CREATE INDEX IF NOT EXISTS idx_merged_old      ON merged_ids(old_tax_id)",
    "CREATE INDEX IF NOT EXISTS idx_host_taxid      ON host_info(tax_id)",
    "CREATE INDEX IF NOT EXISTS idx_typemat_taxid   ON type_material(tax_id)",
]

# 建表顺序（按依赖关系）
TABLE_ORDER = [
    "nodes", "names", "lineage", "zh_names", "extra_zh",
    "divisions", "genetic_codes", "merged_ids", "deleted_ids",
    "host_info", "type_material", "type_of_type", "meta",
]
