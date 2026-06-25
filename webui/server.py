"""
NCBI Taxonomy Web 查询界面
纯标准库实现：http.server + sqlite3 + json
启动后浏览器访问 http://localhost:8520
"""

import json
import os
import sys
import sqlite3
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from taxonomy.config import DEFAULT_DB_PATH, RANK_CN, EXTRA_ZH
from taxonomy.utils import contains_cjk

DB_PATH = DEFAULT_DB_PATH
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))


def get_conn():
    """打开只读数据库连接。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class TaxonomyAPI:
    """处理查询请求，返回 JSON 数据。"""

    @staticmethod
    def search(keyword: str, search_type: str = "auto", limit: int = 30) -> list:
        """搜索物种。
        search_type: auto | zh | latin
        """
        conn = get_conn()
        results = []

        if search_type == "auto":
            if contains_cjk(keyword):
                search_type = "zh"
            else:
                search_type = "latin"

        if search_type == "zh":
            # 先查 extra_zh
            cur = conn.cursor()
            cur.execute("""
                SELECT name_key, zh_name FROM extra_zh
                WHERE zh_name LIKE ?
                LIMIT ?
            """, (f"%{keyword}%", limit))
            for row in cur.fetchall():
                # 用 name_key 反查
                cur2 = conn.cursor()
                cur2.execute(
                    "SELECT tax_id, tax_name, rank FROM lineage WHERE LOWER(tax_name) = ?",
                    (row[0].lower(),))
                lin = cur2.fetchone()
                if lin:
                    results.append({
                        "tax_id": lin[0],
                        "name": lin[1],
                        "zh_name": row[1],
                        "rank": lin[2] or "",
                        "match_type": "zh",
                    })
            conn.close()
            return results[:limit]

        # Latin search
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT n.tax_id, n.name_txt, n.name_class, nd.rank
            FROM names n
            LEFT JOIN nodes nd ON n.tax_id = nd.tax_id
            WHERE n.name_txt LIKE ?
            ORDER BY
                CASE WHEN LOWER(n.name_txt) = LOWER(?) THEN 0
                     WHEN n.name_txt LIKE ? THEN 1
                     ELSE 2 END,
                CASE n.name_class
                    WHEN 'scientific name' THEN 0
                    WHEN 'synonym' THEN 1
                    ELSE 2 END
            LIMIT ?
        """, (f"%{keyword}%", keyword, f"{keyword}%", limit))

        for row in cur.fetchall():
            results.append({
                "tax_id": row[0],
                "name": row[1],
                "name_class": row[2],
                "rank": row[3] or "",
                "match_type": "latin",
            })
        conn.close()
        return results

    @staticmethod
    def info(tax_id: int) -> dict | None:
        """获取物种综合信息。"""
        conn = get_conn()
        cur = conn.cursor()

        # 节点
        cur.execute("""SELECT tax_id, parent_tax_id, rank, division_id
                       FROM nodes WHERE tax_id = ?""", (tax_id,))
        node = cur.fetchone()
        if not node:
            conn.close()
            return None

        # 学名
        cur.execute("""SELECT name_txt FROM names
                       WHERE tax_id = ? AND name_class = 'scientific name'
                       LIMIT 1""", (tax_id,))
        sci = cur.fetchone()
        sci_name = sci[0] if sci else ""

        # 中文名：查 extra_zh + lineage
        zh_name = ""
        cur.execute("SELECT zh_name FROM extra_zh WHERE name_key = ?",
                    (sci_name.lower(),))
        row = cur.fetchone()
        if row:
            zh_name = row[0]

        # 谱系
        cur.execute("""SELECT tax_id, tax_name, species, genus, family, "order",
                       class, phylum, kingdom, domain, taxid_lineage, name_lineage
                       FROM lineage WHERE tax_id = ?""", (tax_id,))
        lineage = cur.fetchone()

        # 祖先链
        ancestors = []
        if lineage and lineage["taxid_lineage"]:
            ids = [int(x) for x in lineage["taxid_lineage"].split() if x.strip()]
            ancestors = TaxonomyAPI._resolve_ancestors(conn, ids)
        else:
            ancestors = TaxonomyAPI._walk_ancestors(conn, tax_id)

        # 子节点数
        cur.execute("SELECT COUNT(*) FROM nodes WHERE parent_tax_id = ?", (tax_id,))
        child_count = cur.fetchone()[0]

        # 所有名称
        cur.execute("""SELECT name_txt, name_class FROM names
                       WHERE tax_id = ? ORDER BY
                       CASE name_class WHEN 'scientific name' THEN 0
                            WHEN 'synonym' THEN 1 ELSE 2 END""", (tax_id,))
        all_names = [{"name": r[0], "class": r[1]} for r in cur.fetchall()]

        # 为祖先补充中文名
        for anc in ancestors:
            if not anc.get("zh_name"):
                anc["zh_name"] = TaxonomyAPI._lookup_zh(conn, anc["name"])

        conn.close()
        return {
            "tax_id": tax_id,
            "scientific_name": sci_name,
            "zh_name": zh_name,
            "rank": node["rank"],
            "rank_cn": RANK_CN.get(node["rank"], node["rank"]),
            "children_count": child_count,
            "ancestors": ancestors,
            "all_names": all_names,
        }

    @staticmethod
    def children(tax_id: int, limit: int = 100) -> list:
        """获取子节点。"""
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT n.tax_id, n.rank,
                   (SELECT name_txt FROM names
                    WHERE tax_id = n.tax_id AND name_class = 'scientific name'
                    LIMIT 1) AS name
            FROM nodes n
            WHERE n.parent_tax_id = ?
            ORDER BY n.tax_id
            LIMIT ?
        """, (tax_id, limit))
        results = []
        for row in cur.fetchall():
            results.append({
                "tax_id": row[0],
                "rank": row[1] or "",
                "rank_cn": RANK_CN.get(row[1], row[1]) if row[1] else "",
                "name": row[2] or "",
                "zh_name": TaxonomyAPI._lookup_zh(conn, row[2]) if row[2] else "",
            })
        conn.close()
        return results

    @staticmethod
    def stats() -> dict:
        """获取数据库统计。"""
        conn = get_conn()
        cur = conn.cursor()
        stats = {}
        for tbl in ["nodes", "names", "lineage", "merged_ids", "deleted_ids"]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            stats[tbl] = cur.fetchone()[0]
        cur.execute("SELECT rank, COUNT(*) AS c FROM nodes GROUP BY rank ORDER BY c DESC LIMIT 15")
        stats["ranks"] = [{"rank": r[0], "cn": RANK_CN.get(r[0], r[0]), "count": r[1]}
                          for r in cur.fetchall()]
        cur.execute("SELECT COUNT(*) FROM extra_zh")
        stats["extra_zh"] = cur.fetchone()[0]
        conn.close()
        return stats

    @staticmethod
    def _resolve_ancestors(conn, ids: list[int]) -> list[dict]:
        """批量解析祖先。"""
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        cur = conn.cursor()
        cur.execute(f"""
            SELECT n.tax_id, n.rank,
                   (SELECT name_txt FROM names
                    WHERE tax_id = n.tax_id AND name_class = 'scientific name'
                    LIMIT 1) AS name
            FROM nodes n WHERE n.tax_id IN ({placeholders})
        """, ids)
        row_map = {}
        for r in cur.fetchall():
            row_map[r[0]] = {
                "tax_id": r[0],
                "name": r[2] or f"ID:{r[0]}",
                "rank": r[1] or "",
                "rank_cn": RANK_CN.get(r[1], r[1]) if r[1] else "",
                "zh_name": "",
            }
        return [row_map[tid] for tid in ids if tid in row_map]

    @staticmethod
    def _walk_ancestors(conn, tax_id: int) -> list[dict]:
        """递归向上遍历。"""
        ancestors = []
        visited = {tax_id}
        cur_id = tax_id
        cur = conn.cursor()
        while cur_id:
            cur.execute("SELECT parent_tax_id FROM nodes WHERE tax_id = ?", (cur_id,))
            row = cur.fetchone()
            if not row:
                break
            pid = row[0]
            if pid == cur_id or pid == 1 or pid in visited:
                break
            visited.add(pid)
            cur.execute("""SELECT n.tax_id, n.rank,
                           (SELECT name_txt FROM names
                            WHERE tax_id = n.tax_id AND name_class = 'scientific name'
                            LIMIT 1) AS name
                           FROM nodes n WHERE n.tax_id = ?""", (pid,))
            r = cur.fetchone()
            if r:
                ancestors.append({
                    "tax_id": r[0],
                    "name": r[2] or f"ID:{r[0]}",
                    "rank": r[1] or "",
                    "rank_cn": RANK_CN.get(r[1], r[1]) if r[1] else "",
                    "zh_name": "",
                })
            cur_id = pid
        ancestors.reverse()
        return ancestors

    @staticmethod
    def _lookup_zh(conn, tax_name: str) -> str:
        """查 extra_zh 词典获取中文名。"""
        if not tax_name:
            return ""
        cur = conn.cursor()
        cur.execute("SELECT zh_name FROM extra_zh WHERE name_key = ?",
                    (tax_name.lower(),))
        row = cur.fetchone()
        return row[0] if row else ""


class RequestHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理。"""

    def log_message(self, format, *args):
        """简化日志。"""
        print(f"  {args[0]}")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode("utf-8"))

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_static(self, path, content_type):
        full = os.path.join(STATIC_DIR, path)
        if not os.path.isfile(full):
            self.send_error(404)
            return
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        try:
            # API 路由
            if path == "/api/search":
                q = params.get("q", [""])[0].strip()
                st = params.get("type", ["auto"])[0]
                limit = int(params.get("limit", [30])[0])
                if not q:
                    self._send_json({"error": "请输入搜索关键词"})
                    return
                results = TaxonomyAPI.search(q, st, limit)
                self._send_json({"results": results, "query": q, "count": len(results)})

            elif path.startswith("/api/info/"):
                tid = int(path.split("/")[-1])
                data = TaxonomyAPI.info(tid)
                if data is None:
                    # 尝试 resolve
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("SELECT new_tax_id FROM merged_ids WHERE old_tax_id = ?", (tid,))
                    row = cur.fetchone()
                    conn.close()
                    if row:
                        data = TaxonomyAPI.info(row[0])
                        if data:
                            data["redirected_from"] = tid
                if data is None:
                    self._send_json({"error": f"TaxID {tid} 不存在"}, 404)
                else:
                    self._send_json(data)

            elif path.startswith("/api/children/"):
                tid = int(path.split("/")[-1])
                limit = int(params.get("limit", [100])[0])
                data = TaxonomyAPI.children(tid, limit)
                self._send_json(data)

            elif path == "/api/stats":
                self._send_json(TaxonomyAPI.stats())

            # 静态文件
            elif path == "/" or path == "/index.html":
                self._send_static("index.html", "text/html; charset=utf-8")
            elif path.endswith(".css"):
                self._send_static(path.lstrip("/"), "text/css; charset=utf-8")
            elif path.endswith(".js"):
                self._send_static(path.lstrip("/"), "application/javascript; charset=utf-8")
            else:
                self._send_json({"error": "Not Found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)


def main():
    if not os.path.isfile(DB_PATH):
        print(f"错误: 数据库不存在 ({DB_PATH})")
        print("请先运行: python -m taxonomy build")
        return 1

    port = 8520
    server = HTTPServer(("127.0.0.1", port), RequestHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"""
╔══════════════════════════════════════════════╗
║     NCBI 物种分类查询系统                      ║
║                                              ║
║  浏览器打开: {url}                       ║
║  按 Ctrl+C 停止服务器                          ║
╚══════════════════════════════════════════════╝
""")
    # 自动打开浏览器
    import webbrowser
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
