"""
AstrBot 物种查询插件 — 接入 NCBI Taxonomy 数据库。
直接调用 taxonomy.TaxonomyQueryEngine Python API，非子进程。

命令:
  /species <名称>        — 按中/英/拉丁名或 TaxID 查询
  /species lineage <名称> — 显示完整分类谱系
  /species children <名称> — 列出直接子节点
  /species stats          — 数据库统计
"""

import os
import sys
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api import logger


class SpeciesPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.engine = None

    def initialize(self):
        """插件加载后初始化 — 设置路径 + 连接数据库。"""
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
            logger.info(f"[species] 数据库已连接: {db_path or DEFAULT_DB_PATH}")
        except ImportError:
            logger.error(
                "[species] 找不到 taxonomy 包，请设置 taxonomy_home 配置项 "
                "或 TAXONOMY_HOME 环境变量"
            )
        except Exception as e:
            logger.error(f"[species] 数据库连接失败: {e}")

    async def terminate(self):
        """插件卸载时关闭数据库。"""
        if self.engine:
            self.engine.close()
            self.engine = None

    # ── 辅助方法 ──────────────────────────────────────────

    def _resolve_name(self, keyword: str) -> int | None:
        """将名称解析为 tax_id。先中文搜，再拉丁搜。返回 tax_id 或 None。"""
        from taxonomy.utils import contains_cjk

        if not keyword.strip():
            return None

        # 纯数字 → 直接当 tax_id
        if keyword.strip().isdigit():
            tid = self.engine.resolve(int(keyword.strip()))
            return tid

        # 含中文 → 先查 extra_zh 词典
        if contains_cjk(keyword):
            results = self.engine.translator.search_by_zh(keyword, limit=5)
            if results:
                return results[0]["tax_id"]

        # 拉丁/英文搜索
        results = self.engine.search_names(keyword, limit=5)
        if results:
            return results[0]["tax_id"]

        return None

    def _search_multi(self, keyword: str, limit: int = 5) -> list[dict]:
        """返回多条匹配结果，供用户选择。"""
        from taxonomy.utils import contains_cjk

        if contains_cjk(keyword):
            return self.engine.translator.search_by_zh(keyword, limit=limit)
        else:
            return self.engine.search_names(keyword, limit=limit)

    @staticmethod
    def _fmt_info(info: dict) -> str:
        """将 get_info() 返回的字典格式化为 QQ 消息文本。"""
        zh = info.get("zh_name", "")
        sci = info.get("scientific_name", "")
        tid = info.get("tax_id", "")
        rank = info.get("rank_cn", info.get("rank", ""))

        header = f"【{zh}】{sci}" if zh else f"【{sci}】"
        lines = [header, f"TaxID: {tid} | Rank: {rank}"]

        for a in info.get("ancestors", []):
            a_zh = a.get("zh_name", "")
            label = f"{a['name']} ({a_zh})" if a_zh else a["name"]
            lines.append(f"{a.get('rank_cn', a.get('rank', ''))}: {label}")

        return "\n".join(lines)

    # ── 命令处理 ──────────────────────────────────────────

    @filter.command_group("species")
    async def species_group(self, event: AstrMessageEvent):
        """主命令组。"""
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=1)

        if len(parts) < 2 or parts[1].strip() in ("help", "帮助"):
            yield event.plain_result(
                "物种查询命令：\n"
                "/species <名称> — 按名称或 TaxID 查询\n"
                "/species lineage <名称> — 完整分类谱系\n"
                "/species children <名称> — 直接子节点\n"
                "/species stats — 数据库统计\n\n"
                "示例: /species 人类  /species 9606  /species E. coli"
            )
            return

        sub = parts[1].strip()
        yield await self._do_query(event, sub)

    @species_group.subcommand("lineage")
    async def species_lineage(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=2)
        keyword = parts[2].strip() if len(parts) > 2 else ""
        if not keyword:
            yield event.plain_result("用法: /species lineage <名称或tax_id>")
            return
        yield await self._do_lineage(event, keyword)

    @species_group.subcommand("children")
    async def species_children(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        parts = msg.split(maxsplit=2)
        keyword = parts[2].strip() if len(parts) > 2 else ""
        if not keyword:
            yield event.plain_result("用法: /species children <名称或tax_id>")
            return
        yield await self._do_children(event, keyword)

    @species_group.subcommand("stats")
    async def species_stats(self, event: AstrMessageEvent):
        yield await self._do_stats(event)

    async def _do_query(self, event, keyword: str):
        """执行物种查询。"""
        if not self.engine:
            yield event.plain_result("[species] 数据库未连接，请检查插件配置。")
            return

        tid = self._resolve_name(keyword)
        if tid is None:
            # 尝试模糊搜索
            results = self._search_multi(keyword)
            if results:
                lines = [f"找到 {len(results)} 个匹配项："]
                for i, r in enumerate(results[:5], 1):
                    name = r.get("zh_name") or r.get("name_txt", "")
                    rank = r.get("rank", "")
                    lines.append(f"{i}. {name} ({r['tax_id']}) — {rank}")
                lines.append("请用 /species id <编号> 查看详情")
                yield event.plain_result("\n".join(lines))
            else:
                yield event.plain_result(f"未找到「{keyword}」的相关信息。")
            return

        info = self.engine.get_info(tid)
        if info is None:
            yield event.plain_result(f"TaxID {tid} 不存在或已被删除。")
            return

        yield event.plain_result(self._fmt_info(info))

    async def _do_lineage(self, event, keyword: str):
        """显示完整谱系树。"""
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

        lines = [f"【{info.get('zh_name') or info['scientific_name']}】分类谱系：\n"]
        for a in info.get("ancestors", []):
            a_zh = a.get("zh_name", "")
            name = f"{a['name']} ({a_zh})" if a_zh else a["name"]
            indent = "  " * (len(lines) - 1)
            lines.append(f"{indent}↳ {a.get('rank_cn', a.get('rank', ''))}: {name}")

        yield event.plain_result("\n".join(lines))

    async def _do_children(self, event, keyword: str):
        """列出子节点。"""
        if not self.engine:
            yield event.plain_result("[species] 数据库未连接。")
            return

        tid = self._resolve_name(keyword)
        if tid is None:
            yield event.plain_result(f"未找到「{keyword}」。")

        children = self.engine.get_children(tid, limit=30)
        if not children:
            yield event.plain_result(f"TaxID {tid} 下无子节点。")
            return

        parent_name = self.engine.get_scientific_name(tid) or f"TaxID {tid}"
        lines = [f"【{parent_name}】的直接子节点 ({len(children)} 个)："]
        for c in children[:20]:
            name = self.engine.get_scientific_name(c.tax_id) or f"ID:{c.tax_id}"
            zh = self.engine.translator.get_zh(c.tax_id)
            label = f"{name} ({zh})" if zh else name
            lines.append(f"  {c.tax_id}  {label}  [{c.rank}]")
        if len(children) > 20:
            lines.append(f"  ... 还有 {len(children) - 20} 个节点")
        yield event.plain_result("\n".join(lines))

    async def _do_stats(self, event):
        """数据库统计。"""
        if not self.engine:
            yield event.plain_result("[species] 数据库未连接。")
            return

        stats = self.engine.get_stats()
        lines = [
            "NCBI 物种数据库统计：",
            f"  节点总数: {stats.get('nodes', 0):,}",
            f"  名称记录: {stats.get('names', 0):,}",
            f"  谱系记录: {stats.get('lineage', 0):,}",
            f"  合并 ID:  {stats.get('merged_ids', 0):,}",
            f"  已删 ID:  {stats.get('deleted_ids', 0):,}",
            f"  中文词典: {stats.get('extra_zh', 0):,}",
            "\n阶元分布 (Top 10)：",
        ]
        for rank, count in (stats.get("rank_dist", []) or [])[:10]:
            lines.append(f"  {rank}: {count:,}")
        yield event.plain_result("\n".join(lines))
