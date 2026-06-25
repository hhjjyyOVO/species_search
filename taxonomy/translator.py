"""中文名翻译层：查询 NCBI 已有中文俗名 + 补充词典"""

import sqlite3
from .config import EXTRA_ZH


class NameTranslator:
    """管理物种中文名的查询和翻译。"""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._zh_cache: dict[int, list[str]] = {}    # tax_id -> [zh_names]
        self._extra_cache: dict[str, str] = dict(EXTRA_ZH)

    def get_zh(self, tax_id: int) -> str:
        """获取单个 tax_id 的中文名（返回第一个可用的）。"""
        names = self.get_zh_all(tax_id)
        return names[0] if names else ""

    def get_zh_all(self, tax_id: int) -> list[str]:
        """获取某个 tax_id 的所有已知中文名。"""
        if tax_id in self._zh_cache:
            return self._zh_cache[tax_id]

        names = []
        # 1. 查 zh_names 表（NCBI 自带中文 common name）
        cur = self.conn.cursor()
        cur.execute("SELECT zh_name FROM zh_names WHERE tax_id = ?", (tax_id,))
        for row in cur.fetchall():
            if row[0] not in names:
                names.append(row[0])

        # 2. 从 lineage 获取 tax_name，查 extra_zh 字典
        if not names:
            cur.execute("SELECT tax_name FROM lineage WHERE tax_id = ?", (tax_id,))
            row = cur.fetchone()
            if row and row[0]:
                key = row[0].lower()
                if key in self._extra_cache:
                    names.append(self._extra_cache[key])

        self._zh_cache[tax_id] = names
        return names

    def batch_get_zh(self, tax_ids: list[int]) -> dict[int, str]:
        """批量获取中文名。返回 {tax_id: zh_name}。"""
        result = {}
        # 先查 zh_names 表
        placeholders = ",".join("?" * len(tax_ids))
        cur = self.conn.cursor()
        cur.execute(
            f"SELECT tax_id, zh_name FROM zh_names WHERE tax_id IN ({placeholders})",
            tax_ids
        )
        for row in cur.fetchall():
            tid, name = row
            if tid not in result:
                result[tid] = name

        # 未命中的查 lineage + extra_zh
        missing = [tid for tid in tax_ids if tid not in result]
        if missing:
            cur.execute(
                f"SELECT tax_id, tax_name FROM lineage WHERE tax_id IN ({placeholders})",
                missing
            )
            for row in cur.fetchall():
                tid, tax_name = row
                if tid not in result:
                    key = tax_name.lower() if tax_name else ""
                    result[tid] = self._extra_cache.get(key, "")

        return result

    def search_by_zh(self, keyword: str, limit: int = 20) -> list[dict]:
        """按中文名搜索（zh_names + extra_zh 字典）。

        步骤：1. 查 extra_zh 中 zh_name 包含 keyword
             2. 用 name_key 精确匹配 lineage.tax_name 获取 tax_id
        """
        cur = self.conn.cursor()
        results = []

        # 1. 在 extra_zh 词典中按 zh_name 模糊搜索
        cur.execute("""
            SELECT name_key, zh_name FROM extra_zh
            WHERE zh_name LIKE ?
            ORDER BY CASE WHEN zh_name = ? THEN 0 ELSE 1 END
            LIMIT ?
        """, (f"%{keyword}%", keyword, limit))

        extra_rows = cur.fetchall()
        for row in extra_rows:
            name_key = row[0]
            zh_name = row[1]
            # 用 name_key 精确匹配 lineage.tax_name（不区分大小写）
            cur2 = self.conn.cursor()
            cur2.execute(
                "SELECT tax_id, tax_name FROM lineage WHERE LOWER(tax_name) = ?",
                (name_key.lower(),))
            lin = cur2.fetchone()
            if lin:
                cur3 = self.conn.cursor()
                cur3.execute("SELECT rank FROM nodes WHERE tax_id = ?", (lin[0],))
                rk = cur3.fetchone()
                results.append({
                    "tax_id": lin[0],
                    "zh_name": zh_name,
                    "scientific_name": lin[1],
                    "rank": rk[0] if rk else "",
                })

        # 2. 补充搜索 zh_names 表（NCBI 自带，目前为空但保留兼容）
        if len(results) < limit:
            cur.execute("""
                SELECT z.tax_id, z.zh_name,
                       (SELECT name_txt FROM names
                        WHERE tax_id = z.tax_id AND name_class = 'scientific name'
                        LIMIT 1) AS tax_name,
                       nd.rank
                FROM zh_names z
                JOIN nodes nd ON z.tax_id = nd.tax_id
                WHERE z.zh_name LIKE ?
                LIMIT ?
            """, (f"%{keyword}%", limit - len(results)))

            for row in cur.fetchall():
                results.append({
                    "tax_id": row[0],
                    "zh_name": row[1],
                    "scientific_name": row[2] or "",
                    "rank": row[3] or "",
                })

        return results[:limit]

    def translate_lineage(self, tax_ids: list[int],
                          zh_map: dict[int, str] = None) -> dict[int, str]:
        """为一组 lineage 节点批量翻译中文名。
        返回 {tax_id: zh_name}。优先用传入的 zh_map。"""
        result = {}
        for tid in tax_ids:
            if zh_map and tid in zh_map:
                result[tid] = zh_map[tid]
            else:
                zh = self.get_zh(tid)
                if zh:
                    result[tid] = zh
        return result
