"""数据模型 dataclass 定义"""

from dataclasses import dataclass, field


@dataclass
class Node:
    """分类节点"""
    tax_id: int
    parent_tax_id: int
    rank: str
    division_id: int | None = None
    genetic_code_id: int | None = None
    mito_GC_id: int | None = None
    genbank_hidden_flag: bool = False
    subtree_hidden_flag: bool = False
    comments: str | None = None
    specified_species: bool = False


@dataclass
class NameInfo:
    """名称信息"""
    tax_id: int
    name_txt: str
    name_class: str
    unique_name: str | None = None


@dataclass
class LineageInfo:
    """分类谱系（各经典阶元 + 完整路径）"""
    tax_id: int
    tax_name: str = ""
    species: str | None = None
    genus: str | None = None
    family: str | None = None
    order: str | None = None
    class_: str | None = None       # Python 安全属性名
    phylum: str | None = None
    kingdom: str | None = None
    domain: str | None = None
    taxid_lineage: str | None = None
    name_lineage: str | None = None

    @classmethod
    def from_row(cls, row: tuple) -> "LineageInfo":
        """从 SQL 查询结果构造"""
        return cls(
            tax_id=row[0], tax_name=row[1] or "",
            species=row[2], genus=row[3], family=row[4],
            order=row[5], class_=row[6], phylum=row[7],
            kingdom=row[8], domain=row[9],
            taxid_lineage=row[10], name_lineage=row[11],
        )
