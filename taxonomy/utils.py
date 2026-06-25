"""文件解析辅助函数和时间/进度工具"""

import io
import re
import sys
import time
from .config import FIELD_SEP, RECORD_SEP


def parse_dmp_line(line: str) -> list[str]:
    """解析一行 dmp 记录，返回字段列表（空字段转为空字符串）。"""
    line = line.rstrip("\n\r")
    # 去掉末尾的 \t|
    if line.endswith("\t|"):
        line = line[:-2]
    # 按 \t|\t 分割
    fields = line.split(FIELD_SEP)
    return fields


def iter_dmp(filepath: str):
    """生成器：逐行读取 dmp 文件，yield 字段列表。"""
    with io.open(filepath, "r", encoding="utf-8", buffering=65536) as f:
        for line in f:
            if not line.strip():
                continue
            yield parse_dmp_line(line)


def progress_bar(current: int, total: int, label: str = "", width: int = 40):
    """打印进度条到 stderr。"""
    if total <= 0:
        return
    pct = min(current / total, 1.0)
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    sys.stderr.write(f"\r  {label} [{bar}] {current:,}/{total:,} ({pct*100:.1f}%)")
    if current >= total:
        sys.stderr.write("\n")
    sys.stderr.flush()


def file_line_count(filepath: str) -> int:
    """快速统计文件行数（用于进度条）。"""
    count = 0
    with io.open(filepath, "r", encoding="utf-8", buffering=1048576) as f:
        for _ in f:
            count += 1
    return count


def contains_cjk(text: str) -> bool:
    """检测文本是否包含 CJK 字符（中文/日文/韩文汉字）。"""
    if not text:
        return False
    return bool(re.search(r'[一-鿿㐀-䶿豈-﫿]', text))


def format_time(seconds: float) -> str:
    """将秒数格式化为可读字符串。"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{int(m)}分{int(s)}秒"
    else:
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        return f"{int(h)}时{int(m)}分{int(s)}秒"
