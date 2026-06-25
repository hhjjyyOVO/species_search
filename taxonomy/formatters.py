"""中文输出格式化：双语表格、树形谱系、信息卡片"""

import json
import sys
from .config import RANK_CN


def print_lineage_tree(info: dict, file=None):
    """打印树形谱系（拉丁名 + 中文名双语）。

    info: core.get_info() 的返回值
    """
    f = file or sys.stdout
    ancestors = info.get("ancestors", [])
    if not ancestors:
        f.write("  (无谱系数据)\n")
        return

    # 构建显示行
    lines = []
    for i, anc in enumerate(ancestors):
        zh = anc.get("zh_name", "")
        name = anc.get("name", "")
        rank = anc.get("rank", "")
        rank_cn = RANK_CN.get(rank, rank)
        prefix = "   " * i

        if zh:
            display = f"{zh} · {name} · {rank_cn}"
        else:
            display = f"{name} · {rank_cn}"
        lines.append((prefix, display, i == len(ancestors) - 1))

    # 输出树
    # 目标节点（树根）
    if lines:
        first = lines[0]
        f.write(f"  {first[1]}\n")

    for i, (prefix, display, is_last) in enumerate(lines[1:], 1):
        connector = "└─ " if is_last else "├─ "
        f.write(f"  {prefix}{connector}{display}\n")

    # 目标节点
    sci = info.get("scientific_name", "")
    zh = info.get("zh_name", "")
    rank = info.get("rank", "")
    rank_cn = RANK_CN.get(rank, rank)
    if zh:
        target = f"{zh} · {sci} · {rank_cn} ★"
    else:
        target = f"{sci} · {rank_cn} ★"

    depth = len(ancestors)
    indent = "   " * depth
    if depth > 0:
        f.write(f"  {indent}└─ {target}\n")
    else:
        f.write(f"  {target}\n")


def print_lineage_table(info: dict, file=None):
    """打印谱系表格（拉丁 + 中文双语对照）。"""
    f = file or sys.stdout
    ancestors = info.get("ancestors", [])
    rank = info.get("rank", "")

    # 组装 all_rows：祖先 + 目标节点自身
    all_rows = []
    for anc in ancestors:
        all_rows.append({
            "rank": anc.get("rank", ""),
            "name": anc.get("name", ""),
            "zh": anc.get("zh_name", ""),
        })
    all_rows.append({
        "rank": rank,
        "name": info.get("scientific_name", ""),
        "zh": info.get("zh_name", ""),
    })

    if not all_rows:
        f.write("  (无谱系数据)\n")
        return

    # 计算列宽
    rank_w = max(max(len(RANK_CN.get(r["rank"], r["rank"])) for r in all_rows), 6)
    latin_w = max(max(len(r["name"]) for r in all_rows), 20)
    zh_w = max(max(len(r["zh"]) for r in all_rows), 8)

    # 表头
    sep = f"  ┌{'─' * rank_w}┬{'─' * latin_w}┬{'─' * zh_w}┐"
    header = f"  │ {'阶元':<{rank_w-2}}│ {'拉丁学名':<{latin_w-4}}│ {'中文名称':<{zh_w-4}}│"
    mid = f"  ├{'─' * rank_w}┼{'─' * latin_w}┼{'─' * zh_w}┤"

    f.write(sep + "\n")
    f.write(header + "\n")
    f.write(mid + "\n")

    for i, r in enumerate(all_rows):
        rank_cn = RANK_CN.get(r["rank"], r["rank"])
        name = r["name"]
        zh = r["zh"]
        marker = "" if i < len(all_rows) - 1 else " ★"
        f.write(f"  │ {rank_cn:<{rank_w-2}}│ {name:<{latin_w-4}}│ {zh:<{zh_w-4}}│{marker}\n")

    bot = f"  └{'─' * rank_w}┴{'─' * latin_w}┴{'─' * zh_w}┘"
    f.write(bot + "\n")


def print_info_card(info: dict, file=None):
    """打印综合信息卡片。"""
    f = file or sys.stdout
    tax_id = info["tax_id"]
    sci_name = info.get("scientific_name", "")
    zh_name = info.get("zh_name", "")
    zh_names = info.get("zh_names", [])
    rank = info.get("rank", "")
    rank_cn = RANK_CN.get(rank, rank)
    division = info.get("division", "")
    children_count = info.get("children_count", 0)

    # 基本卡片
    width = 62
    f.write(f"\n  ╔{'═' * width}╗\n")
    f.write(f"  ║ {'物种信息':^{width-2}} ║\n")
    f.write(f"  ╠{'═' * width}╣\n")
    f.write(f"  ║  Tax ID     : {tax_id:<{width-18}}║\n")
    f.write(f"  ║  学名       : {sci_name:<{width-18}}║\n")

    # 中文名（可能有多个）
    all_zh = [n for n in zh_names if n] if zh_names else ([zh_name] if zh_name else [])
    if all_zh:
        zh_display = " / ".join(all_zh[:5])
        f.write(f"  ║  中文名     : {zh_display:<{width-18}}║\n")

    f.write(f"  ║  分类阶元   : {rank_cn} ({rank}){' ' * max(0, width-18-len(rank_cn)-len(rank)-3)}║\n")
    if division:
        f.write(f"  ║  分区       : {division:<{width-18}}║\n")
    f.write(f"  ║  下级分类数 : {children_count:,}{' ' * max(0, width-18-len(str(children_count))-1)}║\n")

    # 所有名称
    all_names = info.get("all_names", [])
    if all_names:
        f.write(f"  ╟{'─' * width}╢\n")
        f.write(f"  ║  {'所有名称':^{width-2}} ║\n")
        shown = 0
        for n in all_names:
            if shown >= 10:
                break
            cls_cn = _name_class_cn(n["class"])
            line = f"  ║    [{cls_cn}] {n['name']}"
            if len(line) > width + 3:
                line = line[:width + 2] + "…║"
            f.write(f"{line:<{width+4}}║\n")
            shown += 1

    f.write(f"  ╚{'═' * width}╝\n")

    # 谱系树
    ancestors = info.get("ancestors", [])
    if ancestors:
        f.write(f"\n  {'─' * 10} 分类谱系树 {'─' * 10}\n\n")
        print_lineage_tree(info, file=f)

    f.write("\n")


def print_search_results(results: list[dict], keyword: str, file=None):
    """打印搜索结果表格。"""
    f = file or sys.stdout
    if not results:
        f.write(f"  未找到匹配 '{keyword}' 的结果\n")
        return

    f.write(f"\n  搜索 '{keyword}' 找到 {len(results)} 条结果:\n\n")

    # 表头
    f.write(f"  {'Tax ID':>8}  {'名称':<40} {'类型':<20} {'阶元':<16}\n")
    f.write(f"  {'─'*8}  {'─'*40} {'─'*20} {'─'*16}\n")

    for r in results:
        tax_id = r.get("tax_id", "")
        name = r.get("name_txt", "") or r.get("zh_name", "")
        name_class = r.get("name_class", "") or "common name"
        rank = r.get("rank", "")
        rank_cn = RANK_CN.get(rank, rank)
        # 截断长名称
        if len(name) > 40:
            name = name[:37] + "..."
        f.write(f"  {tax_id:>8}  {name:<40} {name_class:<20} {rank_cn:<16}\n")

    f.write("\n")


def print_children_list(children: list, parent_name: str = "",
                        file=None):
    """打印子节点列表。"""
    f = file or sys.stdout
    if not children:
        f.write("  (无子节点)\n")
        return

    f.write(f"\n  子节点 ({len(children)} 个):\n\n")
    f.write(f"  {'Tax ID':>8}  {'阶元':<16} {'名称':<40}\n")
    f.write(f"  {'─'*8}  {'─'*16} {'─'*40}\n")

    from .models import Node
    for child in children:
        rank_cn = RANK_CN.get(child.rank, child.rank)
        tax_id = child.tax_id
        f.write(f"  {tax_id:>8}  {rank_cn:<16} [需查名称]\n")


def print_children_with_names(children_data: list[dict], file=None):
    """打印带名称的子节点列表。"""
    f = file or sys.stdout
    if not children_data:
        f.write("  (无子节点)\n")
        return

    f.write(f"\n  共 {len(children_data)} 个子节点:\n\n")
    f.write(f"  {'Tax ID':>8}  {'阶元':<16} {'名称':<48}\n")
    f.write(f"  {'─'*8}  {'─'*16} {'─'*48}\n")

    for c in children_data:
        rank_cn = RANK_CN.get(c.get("rank", ""), c.get("rank", ""))
        name = c.get("name", "") or c.get("scientific_name", "") or f"ID:{c['tax_id']}"
        if len(name) > 48:
            name = name[:45] + "..."
        f.write(f"  {c['tax_id']:>8}  {rank_cn:<16} {name:<48}\n")
    f.write("\n")


def print_stats(stats: dict, file=None):
    """打印数据库统计。"""
    f = file or sys.stdout
    f.write(f"\n  ╔{'═' * 40}╗\n")
    f.write(f"  ║ {'数据库统计':^36} ║\n")
    f.write(f"  ╠{'═' * 40}╣\n")

    labels = {
        "nodes": "分类节点", "names": "名称条目", "lineage": "谱系记录",
        "zh_names": "中文名", "merged_ids": "合并节点", "deleted_ids": "删除节点",
        "host_info": "宿主关联", "type_material": "模式标本",
    }
    for key, label in labels.items():
        val = stats.get(key, 0)
        f.write(f"  ║  {label:<12}: {val:>15,}   ║\n")

    f.write(f"  ╚{'═' * 40}╝\n")

    # rank 分布
    rank_dist = stats.get("rank_dist", [])
    if rank_dist:
        f.write(f"\n  Top 阶元分布:\n")
        for rank, cnt in rank_dist[:15]:
            rank_cn = RANK_CN.get(rank, rank)
            f.write(f"    {rank_cn:<12} ({rank:<20}) : {cnt:>10,}\n")
    f.write("\n")


def print_json(data: dict | list, file=None):
    """JSON 格式输出（用于程序化使用）。"""
    f = file or sys.stdout
    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    f.write("\n")


def format_full_lineage_bilingual(info: dict) -> str:
    """将完整谱系格式化为双语字符串（供 skill 使用）。"""
    lines = []
    ancestors = info.get("ancestors", [])
    for anc in ancestors:
        name = anc.get("name", "")
        zh = anc.get("zh_name", "")
        rank = anc.get("rank", "")
        rank_cn = RANK_CN.get(rank, rank)
        if zh:
            lines.append(f"{rank_cn}: {name} ({zh})")
        else:
            lines.append(f"{rank_cn}: {name}")

    # 目标
    rank_cn = RANK_CN.get(info.get("rank", ""), info.get("rank", ""))
    sci = info.get("scientific_name", "")
    zh = info.get("zh_name", "")
    if zh:
        lines.append(f"{rank_cn}: {sci} ({zh}) ★ 当前")
    else:
        lines.append(f"{rank_cn}: {sci} ★ 当前")

    return "\n".join(lines)


# ── 内部 ──────────────────────────────────────────────────

def _name_class_cn(cls: str) -> str:
    """name_class 的中文说明。"""
    mapping = {
        "scientific name": "学名",
        "synonym": "异名",
        "common name": "通用名",
        "genbank common name": "GenBank通用名",
        "blast name": "BLAST名",
        "equivalent name": "等效名",
        "authority": "命名人",
        "misspelling": "拼写错误",
        "type material": "模式标本",
        "includes": "包含",
        "in-part": "部分包含",
    }
    return mapping.get(cls, cls)


def _safe_str(s, default=""):
    return s if s else default
