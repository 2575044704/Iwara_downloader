#!/usr/bin/env python3
"""
简单文件查看器 - 只显示文件的前N个字符
"""

import sys
import os

def view_file_head(filepath, num_chars=2500):
    """显示文件的前N个字符"""
    if not os.path.exists(filepath):
        print(f"错误：文件 '{filepath}' 不存在")
        return
    
    file_size = os.path.getsize(filepath)
    print(f"文件: {filepath}")
    print(f"大小: {file_size:,} 字节")
    print(f"显示前 {num_chars} 个字符:")
    print("=" * 80)
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read(num_chars)
        print(content)
    
    print("=" * 80)
    if file_size > num_chars:
        print(f"（还有 {file_size - num_chars:,} 字节未显示）")
    else:
        print("（已显示全部内容）")

def main():
    # 默认文件路径
    filepath = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/iwara_data_pured/chunk_00000.json"
    num_chars = 2500
    
    # 从命令行参数获取
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            num_chars = int(sys.argv[2])
        except ValueError:
            print(f"警告：字符数参数无效，使用默认值 {num_chars}")
    
    view_file_head(filepath, num_chars)

if __name__ == "__main__":
    main()