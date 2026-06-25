"""数据库构建器：从 NCBI .dmp 文件构建 SQLite 数据库"""

import os
import sqlite3
import time
import sys

from .config import (
    DEFAULT_DUMP_DIR, DEFAULT_DB_PATH, SCHEMA_VERSION,
    FIELD_SEP, TABLE_ORDER, DDL, INDEXES, EXTRA_ZH,
)
from .utils import iter_dmp, file_line_count, progress_bar, format_time, contains_cjk


class TaxonomyBuilder:
    """流式读取 NCBI dump 文件，批量写入 SQLite 数据库。"""

    def __init__(self, dump_dir: str = None, db_path: str = None):
        self.dump_dir = dump_dir or DEFAULT_DUMP_DIR
        self.db_path = db_path or DEFAULT_DB_PATH
        self.conn: sqlite3.Connection | None = None
        self._batch_size = 100_000
        # 统计
        self.stats = {}

    # ── 公共入口 ──────────────────────────────────────────

    def build(self) -> dict:
        """执行完整构建，返回统计摘要。"""
        t0 = time.time()
        self._ensure_dump_dir()
        self._open_db()

        print(f"数据库: {self.db_path}")
        print(f"数据源: {self.dump_dir}\n")

        steps = [
            ("创建表结构",     self._create_tables),
            ("加载 divisions",  lambda: self._load_simple("division.dmp", "divisions",
                 ["division_id", "division_code", "division_name"], int_cols=[0])),
            ("加载 gencode",   lambda: self._load_simple("gencode.dmp", "genetic_codes",
                 ["genetic_code_id", "abbreviation", "name", "translation_table", "start_codons"],
                 int_cols=[0])),
            ("加载 merged",    lambda: self._load_simple("merged.dmp", "merged_ids",
                 ["old_tax_id", "new_tax_id"], int_cols=[0, 1])),
            ("加载 delnodes",  lambda: self._load_simple("delnodes.dmp", "deleted_ids",
                 ["tax_id"], int_cols=[0])),
            ("加载 nodes",     self._load_nodes),
            ("加载 names",     self._load_names),
            ("加载 lineage",   self._load_lineage),
            ("提取中文名",     self._extract_zh_names),
            ("写入补充中文名", self._load_extra_zh),
            ("加载 host",      lambda: self._load_simple("host.dmp", "host_info",
                 ["tax_id", "potential_hosts"], int_cols=[0])),
            ("加载 typematerial", lambda: self._load_simple("typematerial.dmp", "type_material",
                 ["tax_id", "tax_name", "type", "identifier"], int_cols=[0])),
            ("加载 typeoftype", lambda: self._load_simple("typeoftype.dmp", "type_of_type",
                 ["type_name", "synonyms", "nomenclature", "description"], skip_cols=[1])),
            ("创建索引",       self._create_indexes),
            ("写入元数据",     self._write_meta),
        ]

        for name, fn in steps:
            t1 = time.time()
            print(f"[{name}] ", end="", flush=True)
            fn()
            elapsed = time.time() - t1
            print(f"完成 ({format_time(elapsed)})")

        # 统计
        self._collect_stats()
        self.conn.commit()
        self.conn.close()

        total_time = time.time() - t0
        print(f"\n[OK] 构建完成，总耗时 {format_time(total_time)}")
        return self.stats

    # ── 内部方法 ──────────────────────────────────────────

    def _ensure_dump_dir(self):
        if not os.path.isdir(self.dump_dir):
            raise FileNotFoundError(f"数据目录不存在: {self.dump_dir}")
        required = ["nodes.dmp", "names.dmp"]
        for f in required:
            p = os.path.join(self.dump_dir, f)
            if not os.path.isfile(p):
                raise FileNotFoundError(f"缺少必要文件: {f}")

    def _open_db(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=OFF")
        self.conn.execute("PRAGMA synchronous=OFF")
        self.conn.execute("PRAGMA cache_size=-500000")   # 500MB cache
        self.conn.execute("PRAGMA page_size=4096")

    def _create_tables(self):
        """建表（先删后建以支持重建）。"""
        cur = self.conn.cursor()
        # 逆序删除
        for tbl in reversed(TABLE_ORDER):
            cur.execute(f"DROP TABLE IF EXISTS {tbl}")
        cur.execute("DROP TABLE IF EXISTS extra_zh")
        # 建表
        for tbl in TABLE_ORDER:
            sql = DDL.get(tbl)
            if sql:
                cur.execute(sql)
        cur.execute(DDL["extra_zh"])
        self.conn.commit()

    def _load_simple(self, filename: str, table: str, columns: list,
                     int_cols: list = None, skip_cols: list = None):
        """加载简单的辅助表（行数少，整体处理）。"""
        filepath = os.path.join(self.dump_dir, filename)
        if not os.path.isfile(filepath):
            print(f"跳过({filename} 不存在) ", end="", flush=True)
            return
        rows = []
        int_cols = set(int_cols or [])
        skip_cols = set(skip_cols or [])
        col_count = len(columns)
        for fields in iter_dmp(filepath):
            if len(fields) < col_count:
                fields += [""] * (col_count - len(fields))
            # 跳过不需要的列
            vals = [v for i, v in enumerate(fields[:col_count]) if i not in skip_cols]
            final_cols = [c for i, c in enumerate(columns) if i not in skip_cols]
            # int 转换
            for i, v in enumerate(vals):
                if i in int_cols:
                    try:
                        vals[i] = int(v)
                    except (ValueError, TypeError):
                        vals[i] = 0
            rows.append(vals)
        if rows:
            placeholders = ",".join(["?"] * len(final_cols))
            cols_sql = ", ".join(f'"{c}"' if c != "order" else '"order"' for c in final_cols)
            self.conn.executemany(
                f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})", rows
            )
        self.conn.commit()
        print(f"{len(rows):,}行 ", end="", flush=True)

    def _load_nodes(self):
        """加载 nodes.dmp（流式，批量插入）。"""
        filepath = os.path.join(self.dump_dir, "nodes.dmp")
        total = file_line_count(filepath)
        print(f"(共 {total:,} 行) ", end="", flush=True)

        cols = ["tax_id", "parent_tax_id", "rank", "embl_code",
                "division_id", "inherited_div", "genetic_code_id",
                "inherited_GC", "mito_GC_id", "inherited_MGC",
                "genbank_hidden_flag", "subtree_hidden_flag",
                "comments", "plastid_GC_id", "inherited_PGC",
                "specified_species", "hydrogenosome_GC_id", "inherited_HGC"]

        # 我们只保留需要的列
        keep_idx = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
        kept_cols = [cols[i] for i in keep_idx]

        sql = """INSERT INTO nodes (tax_id, parent_tax_id, rank, division_id,
                 genetic_code_id, mito_GC_id, genbank_hidden_flag,
                 subtree_hidden_flag, comments, specified_species)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        batch = []
        count = 0
        for fields in iter_dmp(filepath):
            if len(fields) < 18:
                fields += [""] * (18 - len(fields))
            try:
                row = (
                    int_or(fields[0], 0),   # tax_id
                    int_or(fields[1], 1),   # parent_tax_id
                    fields[2] or "no rank", # rank
                    int_or_n(fields[4]),    # division_id
                    int_or_n(fields[6]),    # genetic_code_id
                    int_or_n(fields[8]),    # mito_GC_id
                    int_or(fields[10], 0),  # genbank_hidden_flag
                    int_or(fields[11], 0),  # subtree_hidden_flag
                    fields[12] or None,     # comments
                    int_or(fields[15], 0),  # specified_species
                )
                batch.append(row)
                count += 1
                if len(batch) >= self._batch_size:
                    self.conn.executemany(sql, batch)
                    batch.clear()
                    progress_bar(count, total, "nodes")
            except Exception:
                continue

        if batch:
            self.conn.executemany(sql, batch)
            progress_bar(count, total, "nodes")

        self.conn.commit()
        self.stats["nodes"] = count

    def _load_names(self):
        """加载 names.dmp（流式，批量插入，同时标记中文名）。"""
        filepath = os.path.join(self.dump_dir, "names.dmp")
        total = file_line_count(filepath)
        print(f"(共 {total:,} 行) ", end="", flush=True)

        sql = "INSERT INTO names (tax_id, name_txt, unique_name, name_class) VALUES (?, ?, ?, ?)"
        batch = []
        count = 0
        zh_entries = []  # (tax_id, name_txt)

        for fields in iter_dmp(filepath):
            if len(fields) < 4:
                fields += [""] * (4 - len(fields))
            try:
                tax_id = int_or(fields[0], 0)
                name_txt = fields[1] or ""
                unique = fields[2] or None
                name_class = fields[3] or ""

                batch.append((tax_id, name_txt, unique, name_class))
                count += 1

                # 检测中文名：name_class 是 common name 等 + 含 CJK
                if name_class in ("common name", "genbank common name", "blast name"):
                    if contains_cjk(name_txt):
                        zh_entries.append((tax_id, name_txt))

                if len(batch) >= self._batch_size:
                    self.conn.executemany(sql, batch)
                    batch.clear()
                    progress_bar(count, total, "names")
            except Exception:
                continue

        if batch:
            self.conn.executemany(sql, batch)
            progress_bar(count, total, "names")

        self.conn.commit()
        self.stats["names"] = count

        # 写入中文名表
        if zh_entries:
            self.conn.executemany(
                "INSERT OR IGNORE INTO zh_names (tax_id, zh_name) VALUES (?, ?)",
                zh_entries
            )
        self.conn.commit()
        self.stats["zh_names"] = len(zh_entries)

    def _load_lineage(self):
        """合并 rankedlineage + fullnamelineage + taxidlineage 为 lineage 表。"""
        dump = self.dump_dir

        # ── 先解析 rankedlineage ──
        rl_path = os.path.join(dump, "rankedlineage.dmp")
        fl_path = os.path.join(dump, "fullnamelineage.dmp")
        tl_path = os.path.join(dump, "taxidlineage.dmp")

        has_ranked = os.path.isfile(rl_path)
        has_full = os.path.isfile(fl_path)
        has_taxid = os.path.isfile(tl_path)

        if not has_ranked:
            print("(rankedlineage 不存在，跳过) ", end="", flush=True)
            return

        total = file_line_count(rl_path)
        print(f"(共 {total:,} 行) ", end="", flush=True)

        # 先加载 rankedlineage
        ranked_cols = ["tax_id", "tax_name", "species", "genus", "family",
                       "order", "class", "phylum", "kingdom", "domain"]
        ranked_data = {}  # tax_id -> dict

        for fields in iter_dmp(rl_path):
            if len(fields) < 10:
                fields += [""] * (10 - len(fields))
            try:
                tax_id = int(fields[0])
                ranked_data[tax_id] = {
                    "tax_name": fields[1] or "",
                    "species":  fields[2] or None,
                    "genus":    fields[3] or None,
                    "family":   fields[4] or None,
                    "order":    fields[5] or None,
                    "class":    fields[6] or None,
                    "phylum":   fields[7] or None,
                    "kingdom":  fields[8] or None,
                    "domain":   fields[9] or None,
                }
            except Exception:
                continue

        print("ranked ", end="", flush=True)

        # 补充 fullnamelineage（name_lineage）
        if has_full:
            for fields in iter_dmp(fl_path):
                if len(fields) < 3:
                    continue
                try:
                    tax_id = int(fields[0])
                    if tax_id in ranked_data:
                        ranked_data[tax_id]["name_lineage"] = fields[2].rstrip("; ") or None
                except Exception:
                    continue
            print("fullname ", end="", flush=True)

        # 补充 taxidlineage（taxid_lineage）
        if has_taxid:
            for fields in iter_dmp(tl_path):
                if len(fields) < 2:
                    continue
                try:
                    tax_id = int(fields[0])
                    if tax_id in ranked_data:
                        ranked_data[tax_id]["taxid_lineage"] = fields[1].strip() or None
                except Exception:
                    continue
            print("taxid ", end="", flush=True)

        # 批量写入
        sql = """INSERT INTO lineage (tax_id, tax_name, species, genus, family,
                 "order", class, phylum, kingdom, domain, taxid_lineage, name_lineage)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        batch = []
        count = 0
        for tax_id, d in ranked_data.items():
            batch.append((
                tax_id,
                d["tax_name"],
                d["species"],
                d["genus"],
                d["family"],
                d["order"],
                d["class"],
                d["phylum"],
                d["kingdom"],
                d["domain"],
                d.get("taxid_lineage"),
                d.get("name_lineage"),
            ))
            count += 1
            if len(batch) >= self._batch_size:
                self.conn.executemany(sql, batch)
                batch.clear()
                progress_bar(count, total, "lineage")

        if batch:
            self.conn.executemany(sql, batch)
            progress_bar(count, total, "lineage")

        self.conn.commit()
        self.stats["lineage"] = count

    def _extract_zh_names(self):
        """从 names 表提取中文名到 zh_names（已在 _load_names 中完成，这里是补充去重）。"""
        # 大部分工作在 _load_names 中完成，这里检查去重
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT tax_id || '|' || zh_name) FROM zh_names")
        self.stats["zh_names_unique"] = cur.fetchone()[0]

    def _load_extra_zh(self):
        """写入补充的中文名词典。"""
        rows = [(k, v) for k, v in EXTRA_ZH.items()]
        self.conn.executemany(
            "INSERT OR IGNORE INTO extra_zh (name_key, zh_name) VALUES (?, ?)",
            rows
        )
        self.conn.commit()
        self.stats["extra_zh"] = len(rows)

    def _create_indexes(self):
        """创建所有索引。"""
        cur = self.conn.cursor()
        total = len(INDEXES)
        for i, idx_sql in enumerate(INDEXES):
            cur.execute(idx_sql)
            progress_bar(i + 1, total, "索引")
        self.conn.commit()

    def _write_meta(self):
        """写入元数据。"""
        cur = self.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    ("schema_version", str(SCHEMA_VERSION)))
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    ("built_at", time.strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()

    def _collect_stats(self):
        """收集统计信息。"""
        cur = self.conn.cursor()
        for tbl in ["nodes", "names", "lineage", "zh_names", "merged_ids",
                     "deleted_ids", "host_info", "type_material"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                self.stats[tbl] = cur.fetchone()[0]
            except Exception:
                pass
        try:
            cur.execute("SELECT COUNT(DISTINCT rank) FROM nodes")
            self.stats["unique_ranks"] = cur.fetchone()[0]
        except Exception:
            pass


# ── 辅助函数 ──────────────────────────────────────────────

def int_or(val, default=0):
    """安全 int 转换，失败返回默认值。"""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def int_or_n(val):
    """安全 int 转换，失败或为 0 返回 None。"""
    try:
        v = int(val)
        return v if v != 0 else None
    except (ValueError, TypeError):
        return None
