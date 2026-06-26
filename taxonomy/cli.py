"""命令行接口：argparse 子命令路由"""

import argparse
import os
import sys

from .config import DEFAULT_DB_PATH, DEFAULT_DUMP_DIR, RANK_CN
from .builder import TaxonomyBuilder
from .core import TaxonomyQueryEngine
from .formatters import (
    print_info_card, print_lineage_tree, print_lineage_table,
    print_search_results, print_children_with_names,
    print_stats, print_json, format_full_lineage_bilingual,
)


def main():
    parser = argparse.ArgumentParser(
        prog="taxonomy",
        description="NCBI 物种分类查询系统",
        epilog="环境变量: TAXONOMY_DB | TAXONOMY_DUMP | TAXONOMY_HOME",
    )
    parser.add_argument("--db", default=None,
                        help="SQLite 数据库路径 (默认: $TAXONOMY_DB 或 ./taxonomy.db)")
    parser.add_argument("--dump-dir", default=None,
                        help="dump 目录路径 (默认: $TAXONOMY_DUMP 或 ./new_taxdump/)")

    sub = parser.add_subparsers(dest="cmd", help="可用命令")

    # ── build ──
    p_build = sub.add_parser("build", help="构建/重建数据库")

    # ── lookup ──
    p_lookup = sub.add_parser("lookup", help="按 tax_id 查找节点")
    p_lookup.add_argument("tax_id", type=int)

    # ── search ──
    p_search = sub.add_parser("search", help="按学名搜索")
    p_search.add_argument("keyword")
    p_search.add_argument("--class", dest="name_class", default=None,
                          help="过滤 name_class")
    p_search.add_argument("--limit", type=int, default=30)

    # ── search-zh ──
    p_szh = sub.add_parser("search-zh", help="按中文名搜索")
    p_szh.add_argument("keyword")
    p_szh.add_argument("--limit", type=int, default=20)

    # ── lineage ──
    p_lin = sub.add_parser("lineage", help="显示分类谱系")
    p_lin.add_argument("tax_id", type=int)
    p_lin.add_argument("--format", choices=["tree", "table", "flat", "json"],
                       default="tree")

    # ── children ──
    p_ch = sub.add_parser("children", help="显示直接子节点")
    p_ch.add_argument("tax_id", type=int)
    p_ch.add_argument("--rank", default=None)
    p_ch.add_argument("--limit", type=int, default=200)

    # ── descendants ──
    p_desc = sub.add_parser("descendants", help="显示所有后代")
    p_desc.add_argument("tax_id", type=int)
    p_desc.add_argument("--depth", type=int, default=10)
    p_desc.add_argument("--rank", default=None)
    p_desc.add_argument("--count-only", action="store_true")

    # ── info ──
    p_info = sub.add_parser("info", help="查看物种综合信息卡")
    p_info.add_argument("tax_id", type=int)

    # ── stats ──
    sub.add_parser("stats", help="数据库统计")

    # ── rank ──
    p_rank = sub.add_parser("rank", help="按阶元列出节点")
    p_rank.add_argument("rank_name")
    p_rank.add_argument("--limit", type=int, default=100)

    # ── JSON 全局 ──
    for p in [p_lookup, p_search, p_szh, p_lin, p_ch, p_desc, p_info, p_rank]:
        p.add_argument("--json", action="store_true", help="JSON 格式输出")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return 1

    db_path = args.db or DEFAULT_DB_PATH

    # ── build 不需要数据库 ──
    if args.cmd == "build":
        dump_dir = args.dump_dir or DEFAULT_DUMP_DIR
        builder = TaxonomyBuilder(dump_dir=dump_dir, db_path=db_path)
        try:
            builder.build()
            return 0
        except Exception as e:
            print(f"构建失败: {e}")
            return 1

    # ── 数据库缺失时自动构建 ──
    if not os.path.isfile(db_path):
        print("[!] 数据库不存在，正在自动构建（约 2 分钟）...")
        dump_dir = DEFAULT_DUMP_DIR
        builder = TaxonomyBuilder(dump_dir=dump_dir, db_path=db_path)
        try:
            builder.build()
            print("[OK] 数据库构建完成\n")
        except Exception as e:
            print(f"[X] 构建失败: {e}")
            print("   请确认 new_taxdump/ 目录已包含 NCBI dump 文件")
            print("   下载: https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/")
            print("   镜像: https://ftp.cngb.org/pub/ncbi/taxonomy/")
            return 1

    engine = TaxonomyQueryEngine(db_path)
    try:
        return dispatch(args, engine)
    finally:
        engine.close()


def dispatch(args, engine: TaxonomyQueryEngine) -> int:
    """路由到具体命令处理。"""
    json_out = getattr(args, "json", False)

    if args.cmd == "lookup":
        tid = engine.resolve(args.tax_id)
        if not tid:
            print(f"TaxID {args.tax_id} 不存在或已被删除")
            return 1
        info = engine.get_info(tid)
        if json_out:
            print_json(info)
        else:
            print_info_card(info)

    elif args.cmd == "search":
        results = engine.search_names(args.keyword, args.name_class, args.limit)
        if json_out:
            print_json(results)
        else:
            print_search_results(results, args.keyword)

    elif args.cmd == "search-zh":
        results = engine.translator.search_by_zh(args.keyword, args.limit)
        if json_out:
            print_json(results)
        else:
            print_search_results(
                [{"tax_id": r["tax_id"], "name_txt": r["zh_name"],
                  "name_class": "common name", "rank": r["rank"]}
                 for r in results],
                args.keyword
            )

    elif args.cmd == "lineage":
        tid = engine.resolve(args.tax_id)
        if not tid:
            print(f"TaxID {args.tax_id} 不存在或已被删除")
            return 1
        info = engine.get_info(tid)
        if not info:
            print(f"无法获取 TaxID {tid} 的信息")
            return 1
        fmt = args.format
        if fmt == "json":
            print_json(info)
        elif fmt == "table":
            print_lineage_table(info)
        elif fmt == "flat":
            print(format_full_lineage_bilingual(info))
        else:
            print_lineage_tree(info)

    elif args.cmd == "children":
        tid = engine.resolve(args.tax_id)
        if not tid:
            print(f"TaxID {args.tax_id} 不存在或已被删除")
            return 1
        children = engine.get_children(tid, args.rank, args.limit)
        if json_out:
            print_json([
                {"tax_id": c.tax_id, "parent_tax_id": c.parent_tax_id,
                 "rank": c.rank}
                for c in children
            ])
        else:
            # 附加名称
            data = []
            for c in children:
                name = engine.get_scientific_name(c.tax_id)
                data.append({"tax_id": c.tax_id, "rank": c.rank,
                             "name": name or ""})
            print_children_with_names(data)

    elif args.cmd == "descendants":
        tid = engine.resolve(args.tax_id)
        if not tid:
            print(f"TaxID {args.tax_id} 不存在或已被删除")
            return 1
        if args.count_only:
            cnt = engine.get_subtree_count(tid, args.depth)
            if json_out:
                print_json({"tax_id": tid, "subtree_count": cnt})
            else:
                print(f"  子树节点总数: {cnt:,}")
        else:
            descs = engine.get_descendants(tid, args.depth, args.rank)
            if json_out:
                print_json(descs)
            else:
                print(f"  后代节点: {len(descs)} 个")
                # 附加名称
                data = []
                for d in descs:
                    name = engine.get_scientific_name(d["tax_id"])
                    data.append({**d, "name": name or ""})
                print_children_with_names(data)

    elif args.cmd == "info":
        tid = engine.resolve(args.tax_id)
        if not tid:
            print(f"TaxID {args.tax_id} 不存在或已被删除")
            return 1
        info = engine.get_info(tid)
        if not info:
            print(f"无法获取 TaxID {tid} 的信息")
            return 1
        if json_out:
            print_json(info)
        else:
            print_info_card(info)

    elif args.cmd == "stats":
        stats = engine.get_stats()
        if json_out:
            print_json(stats)
        else:
            print_stats(stats)

    elif args.cmd == "rank":
        nodes = engine.get_by_rank(args.rank_name, args.limit)
        if json_out:
            print_json(nodes)
        else:
            rank_cn = RANK_CN.get(args.rank_name, args.rank_name)
            print(f"\n  阶元 [{rank_cn}] 的节点 (前 {len(nodes)} 个):\n")
            for n in nodes:
                print(f"    {n['tax_id']:>8}  {n['name']}")

    else:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
