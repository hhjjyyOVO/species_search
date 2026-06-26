#!/bin/bash
cd "$(dirname "$0")"

# 检查数据库是否存在
if [ ! -f "taxonomy.db" ]; then
    echo "[!] 数据库未构建，正在自动构建..."
    echo
    python -m taxonomy build
    if [ $? -ne 0 ]; then
        echo
        echo "[X] 数据库构建失败，请确认 new_taxdump 目录包含 NCBI dump 文件"
        echo "    下载: https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/new_taxdump/"
        echo "    镜像: https://ftp.cngb.org/pub/ncbi/taxonomy/"
        exit 1
    fi
    echo
    echo "[OK] 数据库构建完成"
    echo
fi

echo "[*] 正在启动物种分类查询系统..."
echo
python webui/server.py
