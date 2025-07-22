#!/usr/bin/env python3
"""
将大JSON文件中的视频按月份分类，每个视频保存为独立的JSON文件
支持处理多个输入文件

使用方法：
1. 修改脚本中的 input_files 数组
2. 或通过命令行: python script.py file1.json file2.json file3.json output_dir
"""

import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
import sys

def clean_filename(filename):
    """清理文件名，移除非法字符和emoji"""
    # 移除或替换文件系统非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    
    # 移除控制字符
    filename = ''.join(char for char in filename if unicodedata.category(char)[0] != 'C')
    
    # 移除emoji和其他特殊Unicode字符（保留基本的中日韩字符）
    def is_valid_char(char):
        # 保留ASCII字符
        if ord(char) < 128:
            return True
        # 保留中文字符
        if '\u4e00' <= char <= '\u9fff':
            return True
        # 保留日文平假名和片假名
        if '\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff':
            return True
        # 保留韩文
        if '\uac00' <= char <= '\ud7af':
            return True
        # 保留常用标点
        if char in '，。！？；：''""（）【】《》、':
            return True
        return False
    
    filename = ''.join(char if is_valid_char(char) else '_' for char in filename)
    
    # 移除多余的空格和下划线
    filename = re.sub(r'[_\s]+', '_', filename)
    filename = filename.strip('_')
    
    # 如果文件名为空，使用默认名称
    if not filename:
        filename = "untitled"
    
    # 限制文件名长度（考虑UTF-8编码，保守估计）
    # Linux文件名限制是255字节，UTF-8中文最多3字节
    # 保留30字节给.json、可能的编号和路径
    max_bytes = 180
    
    # 按字节截断文件名
    encoded = filename.encode('utf-8')
    if len(encoded) > max_bytes:
        # 逐字符减少直到满足字节限制
        while len(filename.encode('utf-8')) > max_bytes and len(filename) > 0:
            filename = filename[:-1]
        # 清理可能的不完整字符
        filename = filename.rstrip('_')
    
    # 确保文件名不为空
    if not filename:
        filename = "untitled"
    
    return filename

def get_unique_filename(directory, base_name, extension='.json'):
    """获取唯一的文件名，如果存在则添加编号"""
    filename = base_name + extension
    filepath = os.path.join(directory, filename)
    
    if not os.path.exists(filepath):
        return filename
    
    # 如果文件已存在，添加编号
    counter = 1
    while True:
        filename = f"{base_name}_{counter}{extension}"
        filepath = os.path.join(directory, filename)
        if not os.path.exists(filepath):
            return filename
        counter += 1

def process_videos(input_file, output_base_dir='classification'):
    """处理视频文件，按月份分类"""
    print(f"读取文件: {input_file}")
    
    # 创建基础输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 读取JSON文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取JSON文件失败: {e}")
        return None
    
    # 获取视频列表
    if isinstance(data, dict) and 'videos' in data:
        videos = data['videos']
    elif isinstance(data, list):
        videos = data
    else:
        print("未找到视频数据")
        return None
    
    print(f"找到 {len(videos)} 个视频")
    
    # 统计信息
    stats = {
        'total': len(videos),
        'processed': 0,
        'errors': 0,
        'by_month': {}
    }
    
    # 处理每个视频
    for i, video in enumerate(videos):
        try:
            # 获取视频ID和标题
            video_id = video.get('id', f'unknown_{i}')
            title = video.get('title', f'untitled_{i}')
            
            # 获取创建日期
            created_at = video.get('createdAt')
            if not created_at:
                print(f"视频 {video_id} 没有创建日期，跳过")
                stats['errors'] += 1
                continue
            
            # 解析日期，获取年月
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                year_month = dt.strftime('%Y-%m')
            except Exception as e:
                print(f"解析日期失败 {created_at}: {e}")
                stats['errors'] += 1
                continue
            
            # 创建月份目录
            month_dir = os.path.join(output_base_dir, year_month)
            os.makedirs(month_dir, exist_ok=True)
            
            # 清理文件名
            clean_title = clean_filename(title)
            
            # 获取唯一文件名
            filename = get_unique_filename(month_dir, clean_title)
            filepath = os.path.join(month_dir, filename)
            
            # 保存单个视频的JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(video, f, ensure_ascii=False, indent=2)
            
            # 更新统计
            stats['processed'] += 1
            stats['by_month'][year_month] = stats['by_month'].get(year_month, 0) + 1
            
            # 进度显示
            if (i + 1) % 100 == 0:
                print(f"已处理 {i + 1}/{len(videos)} 个视频...")
                
        except Exception as e:
            print(f"处理视频 {i} 时出错: {e}")
            stats['errors'] += 1
    
    # 显示统计结果
    print("\n" + "="*60)
    print("处理完成！")
    print(f"总视频数: {stats['total']}")
    print(f"成功处理: {stats['processed']}")
    print(f"错误数量: {stats['errors']}")
    print("\n按月份统计:")
    for month in sorted(stats['by_month'].keys()):
        print(f"  {month}: {stats['by_month'][month]} 个视频")
    
    return stats

def main():
    # 默认输入文件列表
    input_files = [
        f"/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/iwara_data_pured/chunk_{i:05d}.json"
        for i in range(0, 1)
    ]

    output_dir = "classification"
    
    # 从命令行参数获取
    if len(sys.argv) > 1:
        # 如果有命令行参数，使用命令行指定的文件
        input_files = sys.argv[1:-1] if len(sys.argv) > 2 else [sys.argv[1]]
        if len(sys.argv) > 2:
            output_dir = sys.argv[-1]
    
    # 确认操作
    print("视频分类脚本")
    print(f"输入文件数: {len(input_files)}")
    print(f"输出目录: {output_dir}")
    print("="*60)
    
    # 总体统计
    total_stats = {
        'total': 0,
        'processed': 0,
        'errors': 0,
        'by_month': {}
    }
    
    # 处理每个文件
    for i, input_file in enumerate(input_files):
        print(f"\n处理文件 {i+1}/{len(input_files)}: {input_file}")
        print("-"*60)
        
        # 检查输入文件是否存在
        if not os.path.exists(input_file):
            print(f"错误：输入文件 '{input_file}' 不存在，跳过")
            continue
        
        # 执行处理
        file_stats = process_videos(input_file, output_dir)
        
        # 合并统计
        if file_stats:
            total_stats['total'] += file_stats['total']
            total_stats['processed'] += file_stats['processed']
            total_stats['errors'] += file_stats['errors']
            for month, count in file_stats['by_month'].items():
                total_stats['by_month'][month] = total_stats['by_month'].get(month, 0) + count
    
    # 显示总体统计
    print("\n" + "="*60)
    print("所有文件处理完成！")
    print(f"总视频数: {total_stats['total']}")
    print(f"成功处理: {total_stats['processed']}")
    print(f"错误数量: {total_stats['errors']}")
    print("\n按月份统计:")
    for month in sorted(total_stats['by_month'].keys()):
        print(f"  {month}: {total_stats['by_month'][month]} 个视频")

if __name__ == "__main__":
    main()