"""查询引擎：所有数据库查询操作"""

import sqlite3
from .models import Node, NameInfo, LineageInfo
from .translator import NameTranslator


class TaxonomyQueryEngine:
    """封装所有针对 taxonomy.db 的查询操作。"""

    def __init__(self, db_path: str):
        # 以只读模式打开（支持 WAL 并发读）
        try:
            uri = db_path.replace("\\", "/")
            self.conn = sqlite3.connect(f"file:{uri}?mode=ro", uri=True)
        except Exception:
            self.conn = sqlite3.connect(db_path)
            self.conn.execute("PRAGMA query_only=ON")
        self.conn.row_factory = sqlite3.Row
        self.translator = NameTranslator(self.conn)

    def close(self):
        self.conn.close()

    # ═══════════════════════════════════════════════════════
    # ID 解析
    # ═══════════════════════════════════════════════════════

    def resolve(self, tax_id: int) -> int | None:
        """解析 tax_id：先查 merged，再检查 deleted。返回有效 tax_id 或 None。"""
        cur = self.conn.cursor()
        # 1. 直接存在？
        cur.execute("SELECT 1 FROM nodes WHERE tax_id = ?", (tax_id,))
        if cur.fetchone():
            return tax_id
        # 2. 被合并了？
        cur.execute("SELECT new_tax_id FROM merged_ids WHERE old_tax_id = ?", (tax_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        # 3. 被删了？
        cur.execute("SELECT 1 FROM deleted_ids WHERE tax_id = ?", (tax_id,))
        if cur.fetchone():
            return None
        return None

    # ═══════════════════════════════════════════════════════
    # 节点查询
    # ═══════════════════════════════════════════════════════

    def get_node(self, tax_id: int) -> Node | None:
        """获取节点信息。"""
        cur = self.conn.cursor()
        cur.execute("""SELECT tax_id, parent_tax_id, rank, division_id,
                       genetic_code_id, mito_GC_id, genbank_hidden_flag,
                       subtree_hidden_flag, comments, specified_species
                       FROM nodes WHERE tax_id = ?""", (tax_id,))
        row = cur.fetchone()
        if not row:
            return None
        return Node(
            tax_id=row[0], parent_tax_id=row[1], rank=row[2],
            division_id=row[3], genetic_code_id=row[4], mito_GC_id=row[5],
            genbank_hidden_flag=bool(row[6]), subtree_hidden_flag=bool(row[7]),
            comments=row[8], specified_species=bool(row[9]),
        )

    # ═══════════════════════════════════════════════════════
    # 名称查询
    # ═══════════════════════════════════════════════════════

    def get_names(self, tax_id: int) -> list[NameInfo]:
        """获取某节点的所有名称（按优先级排序）。"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT tax_id, name_txt, unique_name, name_class
            FROM names WHERE tax_id = ?
            ORDER BY
                CASE name_class
                    WHEN 'scientific name' THEN 0
                    WHEN 'synonym' THEN 1
                    WHEN 'genbank common name' THEN 2
                    WHEN 'common name' THEN 3
                    WHEN 'blast name' THEN 4
                    ELSE 5 END
        """, (tax_id,))
        return [NameInfo(tax_id=r[0], name_txt=r[1], unique_name=r[2], name_class=r[3])
                for r in cur.fetchall()]

    def get_scientific_name(self, tax_id: int) -> str | None:
        """获取学名。"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT name_txt FROM names WHERE tax_id = ? AND name_class = 'scientific name'",
            (tax_id,))
        row = cur.fetchone()
        return row[0] if row else None

    def search_names(self, keyword: str, name_class: str = None,
                     limit: int = 30) -> list[dict]:
        """按学名搜索（模糊匹配）。"""
        cur = self.conn.cursor()
        if name_class:
            cur.execute("""
                SELECT DISTINCT n.tax_id, n.name_txt, n.name_class, nd.rank
                FROM names n
                LEFT JOIN nodes nd ON n.tax_id = nd.tax_id
                WHERE n.name_txt LIKE ? AND n.name_class = ?
                ORDER BY
                    CASE WHEN n.name_txt = ? THEN 0
                         WHEN n.name_txt LIKE ? THEN 1
                         ELSE 2 END
                LIMIT ?
            """, (f"%{keyword}%", name_class, keyword, f"{keyword}%", limit))
        else:
            cur.execute("""
                SELECT DISTINCT n.tax_id, n.name_txt, n.name_class, nd.rank
                FROM names n
                LEFT JOIN nodes nd ON n.tax_id = nd.tax_id
                WHERE n.name_txt LIKE ?
                ORDER BY
                    CASE WHEN n.name_txt = ? THEN 0
                         WHEN n.name_txt LIKE ? THEN 1
                         ELSE 2 END
                LIMIT ?
            """, (f"%{keyword}%", keyword, f"{keyword}%", limit))

        return [dict(row) for row in cur.fetchall()]

    # ═══════════════════════════════════════════════════════
    # 谱系查询
    # ═══════════════════════════════════════════════════════

    def get_lineage(self, tax_id: int) -> LineageInfo | None:
        """获取完整谱系信息。"""
        cur = self.conn.cursor()
        cur.execute("""SELECT tax_id, tax_name, species, genus, family, "order",
                       class, phylum, kingdom, domain, taxid_lineage, name_lineage
                       FROM lineage WHERE tax_id = ?""", (tax_id,))
        row = cur.fetchone()
        if not row:
            return None
        return LineageInfo.from_row(row)

    def get_ancestors(self, tax_id: int) -> list[dict]:
        """获取祖先节点链（从根到目标节点，不含目标）。
        返回 [{tax_id, name, rank}, ...]。"""
        lineage = self.get_lineage(tax_id)
        if not lineage or not lineage.taxid_lineage:
            return self._walk_ancestors(tax_id)
        # 从 taxid_lineage 解析
        ids = [int(x) for x in lineage.taxid_lineage.split() if x.strip()]
        if not ids:
            return self._walk_ancestors(tax_id)
        return self._resolve_ancestor_info(ids)

    def _walk_ancestors(self, tax_id: int) -> list[dict]:
        """递归向上遍历获取祖先链。"""
        ancestors = []
        visited = set()
        cur_id = tax_id
        while cur_id and cur_id not in visited:
            visited.add(cur_id)
            node = self.get_node(cur_id)
            if not node:
                break
            parent_id = node.parent_tax_id
            if parent_id == cur_id:
                break
            cur_id = parent_id
            if cur_id != tax_id:
                name = self.get_scientific_name(cur_id)
                ancestors.append({"tax_id": cur_id, "name": name or f"ID:{cur_id}",
                                  "rank": ""})
        ancestors.reverse()
        return ancestors

    def _resolve_ancestor_info(self, ids: list[int]) -> list[dict]:
        """用一批 tax_id 查节点名和 rank。"""
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        cur = self.conn.cursor()
        cur.execute(f"""
            SELECT n.tax_id,
                   (SELECT name_txt FROM names WHERE tax_id = n.tax_id
                    AND name_class = 'scientific name' LIMIT 1) AS name,
                   n.rank
            FROM nodes n
            WHERE n.tax_id IN ({placeholders})
            ORDER BY n.tax_id
        """, ids)
        # 保持原顺序
        row_map = {}
        for row in cur.fetchall():
            row_map[row[0]] = {"tax_id": row[0], "name": row[1] or f"ID:{row[0]}",
                               "rank": row[2] or ""}
        return [row_map[tid] for tid in ids if tid in row_map]

    # ═══════════════════════════════════════════════════════
    # 树导航
    # ═══════════════════════════════════════════════════════

    def get_children(self, tax_id: int, rank_filter: str = None,
                     limit: int = 200) -> list[Node]:
        """获取直接子节点。"""
        cur = self.conn.cursor()
        if rank_filter:
            cur.execute("""SELECT tax_id, parent_tax_id, rank, division_id,
                           genetic_code_id, mito_GC_id, genbank_hidden_flag,
                           subtree_hidden_flag, comments, specified_species
                           FROM nodes WHERE parent_tax_id = ? AND rank = ?
                           LIMIT ?""", (tax_id, rank_filter, limit))
        else:
            cur.execute("""SELECT tax_id, parent_tax_id, rank, division_id,
                           genetic_code_id, mito_GC_id, genbank_hidden_flag,
                           subtree_hidden_flag, comments, specified_species
                           FROM nodes WHERE parent_tax_id = ?
                           LIMIT ?""", (tax_id, limit))
        return [Node(tax_id=r[0], parent_tax_id=r[1], rank=r[2],
                     division_id=r[3], genetic_code_id=r[4], mito_GC_id=r[5],
                     genbank_hidden_flag=bool(r[6]), subtree_hidden_flag=bool(r[7]),
                     comments=r[8], specified_species=bool(r[9]))
                for r in cur.fetchall()]

    def get_children_count(self, tax_id: int) -> int:
        """获取直接子节点数量。"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM nodes WHERE parent_tax_id = ?", (tax_id,))
        return cur.fetchone()[0]

    def get_descendants(self, tax_id: int, max_depth: int = 10,
                        rank_filter: str = None,
                        limit: int = 500) -> list[dict]:
        """递归获取所有后代节点。"""
        cur = self.conn.cursor()
        if rank_filter:
            cur.execute("""
                WITH RECURSIVE subtree(tax_id, parent_tax_id, rank, depth) AS (
                    SELECT tax_id, parent_tax_id, rank, 0
                    FROM nodes WHERE tax_id = ?
                    UNION ALL
                    SELECT n.tax_id, n.parent_tax_id, n.rank, s.depth + 1
                    FROM nodes n JOIN subtree s ON n.parent_tax_id = s.tax_id
                    WHERE s.depth < ?
                )
                SELECT tax_id, parent_tax_id, rank, depth
                FROM subtree WHERE depth > 0 AND rank = ?
                LIMIT ?
            """, (tax_id, max_depth, rank_filter, limit))
        else:
            cur.execute("""
                WITH RECURSIVE subtree(tax_id, parent_tax_id, rank, depth) AS (
                    SELECT tax_id, parent_tax_id, rank, 0
                    FROM nodes WHERE tax_id = ?
                    UNION ALL
                    SELECT n.tax_id, n.parent_tax_id, n.rank, s.depth + 1
                    FROM nodes n JOIN subtree s ON n.parent_tax_id = s.tax_id
                    WHERE s.depth < ?
                )
                SELECT tax_id, parent_tax_id, rank, depth
                FROM subtree WHERE depth > 0
                LIMIT ?
            """, (tax_id, max_depth, limit))
        return [dict(row) for row in cur.fetchall()]

    def get_subtree_count(self, tax_id: int, max_depth: int = 50) -> int:
        """统计子树中所有节点数量。"""
        cur = self.conn.cursor()
        cur.execute("""
            WITH RECURSIVE subtree(tax_id) AS (
                SELECT tax_id FROM nodes WHERE tax_id = ?
                UNION ALL
                SELECT n.tax_id FROM nodes n
                JOIN subtree s ON n.parent_tax_id = s.tax_id
                LIMIT 1000000
            )
            SELECT COUNT(*) - 1 FROM subtree
        """, (tax_id,))
        row = cur.fetchone()
        return max(0, row[0]) if row else 0

    # ═══════════════════════════════════════════════════════
    # 阶元查询
    # ═══════════════════════════════════════════════════════

    def get_by_rank(self, rank: str, limit: int = 100,
                    offset: int = 0) -> list[dict]:
        """列出指定阶元的所有节点。"""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT n.tax_id, n.rank,
                   (SELECT name_txt FROM names WHERE tax_id = n.tax_id
                    AND name_class = 'scientific name' LIMIT 1) AS name
            FROM nodes n
            WHERE n.rank = ?
            ORDER BY n.tax_id
            LIMIT ? OFFSET ?
        """, (rank, limit, offset))
        return [dict(row) for row in cur.fetchall()]

    # ═══════════════════════════════════════════════════════
    # 综合信息
    # ═══════════════════════════════════════════════════════

    def get_info(self, tax_id: int) -> dict | None:
        """获取综合信息卡所需的所有数据。"""
        node = self.get_node(tax_id)
        if not node:
            return None

        names = self.get_names(tax_id)
        lineage = self.get_lineage(tax_id)
        children_count = self.get_children_count(tax_id)

        # 中文名
        zh_names = self.translator.get_zh_all(tax_id)
        zh_name = zh_names[0] if zh_names else ""

        # 分区名
        div_name = ""
        if node.division_id:
            cur = self.conn.cursor()
            cur.execute("SELECT division_name FROM divisions WHERE division_id = ?",
                        (node.division_id,))
            row = cur.fetchone()
            if row:
                div_name = row[0]

        # 谱系双语化
        ancestors = []
        if lineage:
            # 用 ranked 阶元组装谱系
            rank_order = ["domain", "kingdom", "phylum", "class",
                          "order", "family", "genus", "species"]
            lin_dict = {
                "domain": lineage.domain,
                "kingdom": lineage.kingdom,
                "phylum": lineage.phylum,
                "class": lineage.class_,
                "order": lineage.order,
                "family": lineage.family,
                "genus": lineage.genus,
                "species": lineage.species,
            }
            # 收集需要翻译的 ancestor tax_ids
            anc_list = self.get_ancestors(tax_id)

            for anc in anc_list:
                ancestors.append({
                    "tax_id": anc["tax_id"],
                    "name": anc["name"],
                    "rank": anc["rank"],
                    "zh_name": self.translator.get_zh(anc["tax_id"]),
                })

        return {
            "tax_id": tax_id,
            "scientific_name": self._pick_sci_name(names),
            "zh_name": zh_name,
            "zh_names": zh_names,
            "rank": node.rank,
            "division": div_name,
            "all_names": [{"name": n.name_txt, "class": n.name_class} for n in names],
            "ancestors": ancestors,
            "children_count": children_count,
            "lineage": {k: v for k, v in (lineage.__dict__ if lineage else {}).items()},
        }

    def _pick_sci_name(self, names: list[NameInfo]) -> str:
        for n in names:
            if n.name_class == "scientific name":
                return n.name_txt
        return names[0].name_txt if names else ""

    # ═══════════════════════════════════════════════════════
    # 统计
    # ═══════════════════════════════════════════════════════

    def get_stats(self) -> dict:
        """获取数据库统计信息。"""
        cur = self.conn.cursor()
        stats = {}
        for tbl in ["nodes", "names", "lineage", "zh_names", "merged_ids",
                     "deleted_ids", "host_info", "type_material"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                stats[tbl] = cur.fetchone()[0]
            except Exception:
                stats[tbl] = 0

        # rank 分布 top 20
        try:
            cur.execute("""
                SELECT rank, COUNT(*) AS cnt FROM nodes
                GROUP BY rank ORDER BY cnt DESC LIMIT 20
            """)
            stats["rank_dist"] = [(r["rank"], r["cnt"]) for r in cur.fetchall()]
        except Exception:
            stats["rank_dist"] = []
        return stats
