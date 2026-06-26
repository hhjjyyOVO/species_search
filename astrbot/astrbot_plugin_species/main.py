"""
AstrBot 物种查询插件 — 接入 NCBI Taxonomy 数据库。

双模式：
  LLM Tool  — 用户自然语言提问 → 插件取数据 → LLM 人格回复（附带翻译）
  Command   — /species <名称>  直接查询（结构化输出）

环境变量 / 配置:
  TAXONOMY_HOME — taxonomy/ 包所在目录
  TAXONOMY_DB   — taxonomy.db 路径
"""

import os
import sys

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger


class SpeciesPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.engine = None

    async def initialize(self):
        """加载插件 — 设置路径 + 连接数据库。"""
        tax_home = self.config.get("taxonomy_home", "").strip()
        if tax_home:
            p = os.path.abspath(os.path.expanduser(tax_home))
        else:
            p = os.environ.get("TAXONOMY_HOME", "")
        if p and p not in sys.path:
            sys.path.insert(0, p)

        db_path = (
            self.config.get("db_path", "").strip()
            or os.environ.get("TAXONOMY_DB", "")
            or None
        )

        try:
            from taxonomy.core import TaxonomyQueryEngine
            from taxonomy.config import DEFAULT_DB_PATH
            self.engine = TaxonomyQueryEngine(db_path or DEFAULT_DB_PATH)
            logger.info(f"[species] DB connected: {db_path or DEFAULT_DB_PATH}")
        except ImportError:
            logger.error("[species] taxonomy package not found — set taxonomy_home or TAXONOMY_HOME")
        except Exception as e:
            logger.error(f"[species] DB connect failed: {e}")

    async def terminate(self):
        if self.engine:
            self.engine.close()
            self.engine = None

    # ═══════════════════════════════════════════════════════
    #  LLM Tools — 返回结构化数据，由 LLM 人格自然语言化
    # ═══════════════════════════════════════════════════════

    @filter.llm_tool(name="query_species")
    async def query_species(self, event: AstrMessageEvent, name: str) -> str:
        '''查询物种分类信息。返回人类可读的文本格式结果。

        Args:
            name(string): 物种名称（中文如"人类"、拉丁如"Homo sapiens"）或纯数字 TaxID
        '''
        if not self.engine:
            return "数据库未连接，请联系管理员检查插件配置。"

        tid = self._resolve_name(name)
        if tid is None:
            results = self._search_multi(name, limit=8)
            if results:
                lines = [f"「{name}」找到 {len(results)} 个匹配项："]
                for i, r in enumerate(results[:5], 1):
                    label = r.get("zh_name") or r.get("name_txt", "")
                    lines.append(f"{i}. {label} (TaxID: {r['tax_id']}) [{r.get('rank', '')}]")
                lines.append("请回复序号或 TaxID 查看详情。")
                return "\n".join(lines)
            return f"未找到「{name}」的信息。请尝试拉丁学名或英文名。"

        info = self.engine.get_info(tid)
        if info is None:
            return f"TaxID {tid} 不存在或已被删除。"

        return self._fmt_info_text(info)

    @filter.llm_tool(name="query_species_by_id")
    async def query_species_by_id(self, event: AstrMessageEvent, tax_id: int) -> str:
        '''按 NCBI Taxonomy ID 查询物种详情。

        Args:
            tax_id(number): NCBI Taxonomy ID
        '''
        if not self.engine:
            return "数据库未连接。"

        tid = self.engine.resolve(tax_id)
        if tid is None:
            return f"TaxID {tax_id} 不存在或已被删除。"

        info = self.engine.get_info(tid)
        if info is None:
            return f"TaxID {tid} 不存在。"

        return self._fmt_info_text(info)

    @filter.llm_tool(name="species_lineage")
    async def species_lineage(self, event: AstrMessageEvent, name: str) -> str:
        '''查询物种完整分类谱系。返回树形文本。

        Args:
            name(string): 物种名称或 TaxID
        '''
        if not self.engine:
            return "数据库未连接。"

        tid = self._resolve_name(name)
        if tid is None:
            return f"未找到「{name}」。"

        info = self.engine.get_info(tid)
        if info is None:
            return f"TaxID {tid} 不存在。"

        return self._fmt_lineage_text(info)

    @filter.llm_tool(name="species_stats")
    async def species_stats(self, event: AstrMessageEvent) -> str:
        '''查询 NCBI 物种数据库统计信息。'''
        if not self.engine:
            return "数据库未连接。"

        stats = self.engine.get_stats()
        lines = [
            "NCBI 物种数据库统计：",
            f"  节点总数: {stats.get('nodes', 0):,}",
            f"  名称记录: {stats.get('names', 0):,}",
            f"  谱系记录: {stats.get('lineage', 0):,}",
            f"  合并 ID:  {stats.get('merged_ids', 0):,}",
            f"  已删 ID:  {stats.get('deleted_ids', 0):,}",
            f"  中文词典: {stats.get('extra_zh', 0):,}",
        ]
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    #  Commands — 显式命令
    # ═══════════════════════════════════════════════════════

    @filter.command("species")
    async def species_cmd(self, event: AstrMessageEvent):
        '''查询物种分类信息。用法: /species <名称或tax_id>'''
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)

        if len(parts) < 2 or parts[1].strip() in ("help", "帮助"):
            yield event.plain_result(
                "🌿 物种查询命令：\n"
                "/species <名称>       — 查询物种信息\n"
                "/lineage <名称>       — 完整分类谱系\n"
                "/children <名称>      — 直接子节点\n"
                "/taxonomy_stats       — 数据库统计\n\n"
                "也可以直接用自然语言问我，如「人类是什么物种」"
            )
            return

        keyword = parts[1].strip()
        async for msg in self._do_query(event, keyword):
            yield msg

    @filter.command("lineage")
    async def species_lineage_cmd(self, event: AstrMessageEvent):
        '''查询物种完整分类谱系。用法: /lineage <名称或tax_id>'''
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)
        keyword = parts[1].strip() if len(parts) > 1 else ""
        if not keyword:
            yield event.plain_result("用法: /lineage <名称或tax_id>")
            return
        async for msg in self._do_lineage(event, keyword):
            yield msg

    @filter.command("children")
    async def species_children_cmd(self, event: AstrMessageEvent):
        '''列出分类节点下的子节点。用法: /children <名称或tax_id>'''
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)
        keyword = parts[1].strip() if len(parts) > 1 else ""
        if not keyword:
            yield event.plain_result("用法: /children <名称或tax_id>")
            return
        async for msg in self._do_children(event, keyword):
            yield msg

    @filter.command("taxonomy_stats")
    async def species_stats_cmd(self, event: AstrMessageEvent):
        '''NCBI 物种数据库统计。'''
        async for msg in self._do_stats(event):
            yield msg

    # ═══════════════════════════════════════════════════════
    #  Internal
    # ═══════════════════════════════════════════════════════

    def _resolve_name(self, keyword: str) -> int | None:
        """名称 → tax_id。中文→extra_zh→search-zh；拉丁→search_names；纯数字→tax_id。"""
        from taxonomy.utils import contains_cjk

        kw = keyword.strip()
        if not kw:
            return None
        if kw.isdigit():
            return self.engine.resolve(int(kw))

        if contains_cjk(kw):
            results = self.engine.translator.search_by_zh(kw, limit=3)
            if results:
                return results[0]["tax_id"]

        results = self.engine.search_names(kw, limit=3)
        if results:
            return results[0]["tax_id"]
        return None

    def _search_multi(self, keyword: str, limit: int = 8) -> list[dict]:
        from taxonomy.utils import contains_cjk
        if contains_cjk(keyword):
            return self.engine.translator.search_by_zh(keyword, limit=limit)
        else:
            return self.engine.search_names(keyword, limit=limit)

    async def _do_query(self, event, keyword: str):
        if not self.engine:
            yield event.plain_result("[species] 数据库未连接。")
            return

        tid = self._resolve_name(keyword)
        if tid is None:
            results = self._search_multi(keyword)
            if results:
                lines = [f"找到 {len(results)} 个匹配项："]
                for i, r in enumerate(results[:5], 1):
                    name = r.get("zh_name") or r.get("name_txt", "")
                    lines.append(f"{i}. {name} (TaxID: {r['tax_id']}) [{r.get('rank', '')}]")
                lines.append("\n用 /species id <编号> 查看详情")
                yield event.plain_result("\n".join(lines))
            else:
                yield event.plain_result(f"未找到「{keyword}」。")
            return

        info = self.engine.get_info(tid)
        if info is None:
            yield event.plain_result(f"TaxID {tid} 不存在。")
            return
        yield event.plain_result(self._fmt_info_text(info))

    async def _do_lineage(self, event, keyword: str):
        if not self.engine:
            yield event.plain_result("[species] 数据库未连接。")
            return
        tid = self._resolve_name(keyword)
        if tid is None:
            yield event.plain_result(f"未找到「{keyword}」。")
            return
        info = self.engine.get_info(tid)
        if info is None:
            yield event.plain_result(f"TaxID {tid} 不存在。")
            return
        yield event.plain_result(self._fmt_lineage_text(info))

    async def _do_children(self, event, keyword: str):
        if not self.engine:
            yield event.plain_result("[species] 数据库未连接。")
            return
        tid = self._resolve_name(keyword)
        if tid is None:
            yield event.plain_result(f"未找到「{keyword}」。")
            return
        children = self.engine.get_children(tid, limit=30)
        if not children:
            yield event.plain_result(f"TaxID {tid} 下无子节点。")
            return
        pname = self.engine.get_scientific_name(tid) or f"TaxID {tid}"
        lines = [f"【{pname}】的子节点 ({len(children)} 个)："]
        for c in children[:20]:
            name = self.engine.get_scientific_name(c.tax_id) or f"ID:{c.tax_id}"
            zh = self.engine.translator.get_zh(c.tax_id)
            label = f"{name} ({zh})" if zh else name
            lines.append(f"  {c.tax_id}  {label}  [{c.rank}]")
        if len(children) > 20:
            lines.append(f"  ... 还有 {len(children) - 20} 个")
        yield event.plain_result("\n".join(lines))

    async def _do_stats(self, event):
        if not self.engine:
            yield event.plain_result("[species] 数据库未连接。")
            return
        stats = self.engine.get_stats()
        lines = [
            "NCBI 物种数据库统计：",
            f"  节点: {stats.get('nodes', 0):,}",
            f"  名称: {stats.get('names', 0):,}",
            f"  谱系: {stats.get('lineage', 0):,}",
            f"  合并: {stats.get('merged_ids', 0):,}",
            f"  已删: {stats.get('deleted_ids', 0):,}",
            f"  中文: {stats.get('extra_zh', 0):,}",
        ]
        yield event.plain_result("\n".join(lines))

    @staticmethod
    def _rank_cn(rank: str) -> str:
        """rank → 中文名，在 RANK_CN 不可用时的后备。"""
        try:
            from taxonomy.config import RANK_CN
            return RANK_CN.get(rank, rank)
        except ImportError:
            return rank

    @classmethod
    def _fmt_info_text(cls, info: dict) -> str:
        zh = info.get("zh_name", "")
        sci = info.get("scientific_name", "")
        tid = info.get("tax_id", "")
        rank = info.get("rank_cn") or cls._rank_cn(info.get("rank", ""))
        header = f"【{zh}】{sci}" if zh else f"【{sci}】"
        lines = [header, f"TaxID: {tid} | Rank: {rank}"]
        for a in info.get("ancestors", []):
            a_zh = a.get("zh_name", "")
            label = f"{a['name']} ({a_zh})" if a_zh else a["name"]
            rc = a.get("rank_cn") or cls._rank_cn(a.get("rank", ""))
            lines.append(f"{rc}: {label}")
        return "\n".join(lines)

    @classmethod
    def _fmt_lineage_text(cls, info: dict) -> str:
        label = info.get("zh_name") or info["scientific_name"]
        lines = [f"【{label}】分类谱系：\n"]
        for a in info.get("ancestors", []):
            a_zh = a.get("zh_name", "")
            name = f"{a['name']} ({a_zh})" if a_zh else a["name"]
            rc = a.get("rank_cn") or cls._rank_cn(a.get("rank", ""))
            indent = "  " * (len(lines) - 1)
            lines.append(f"{indent}↳ {rc}: {name}")
        return "\n".join(lines)
