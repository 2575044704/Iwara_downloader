#!/usr/bin/env python3
"""
视频过滤和分析工具
用于筛选和分析特定类型的视频
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def format_size(bytes):
    """格式化文件大小"""
    if bytes == 0:
        return "0 B"
    elif bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes/1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes/1024/1024:.1f} MB"
    else:
        return f"{bytes/1024/1024/1024:.1f} GB"

def analyze_videos(filepath):
    """分析视频数据，特别关注会员内容和问题视频"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or "videos" not in data:
            print("文件格式错误")
            return
        
        videos = data["videos"]
        print(f"总视频数: {len(videos)}\n")
        
        # 分类统计
        categories = {
            "normal": [],           # 正常视频
            "no_file": [],         # 没有文件信息
            "zero_size": [],       # 文件大小为0
            "gold_member": [],     # 金牌会员视频
            "private": [],         # 私密视频
            "unlisted": []         # 未列出视频
        }
        
        # 分析每个视频
        for i, video in enumerate(videos):
            title = video.get("title", "")
            
            # 检查是否是会员视频
            if "[Gold Member]" in title or "[gold member]" in title.lower():
                categories["gold_member"].append((i, video))
            
            # 检查私密状态
            if video.get("private"):
                categories["private"].append((i, video))
            
            if video.get("unlisted"):
                categories["unlisted"].append((i, video))
            
            # 检查文件信息
            file_info = video.get("file")
            if file_info is None:
                categories["no_file"].append((i, video))
            elif isinstance(file_info, dict):
                size = file_info.get("size", 0)
                if size == 0:
                    categories["zero_size"].append((i, video))
                else:
                    categories["normal"].append((i, video))
            
        # 显示统计结果
        print("📊 视频分类统计:")
        print(f"  ✅ 正常视频: {len(categories['normal'])}")
        print(f"  ❌ 无文件信息: {len(categories['no_file'])}")
        print(f"  ⚠️  文件大小为0: {len(categories['zero_size'])}")
        print(f"  👑 Gold Member: {len(categories['gold_member'])}")
        print(f"  🔒 私密视频: {len(categories['private'])}")
        print(f"  📝 未列出: {len(categories['unlisted'])}")
        
        # 显示问题视频详情
        print("\n❌ 无文件信息的视频:")
        for idx, (i, video) in enumerate(categories["no_file"][:10]):
            print(f"  #{i+1}: {video.get('title', '无标题')[:60]}...")
            print(f"       观看: {video.get('numViews', 0):,} | ID: {video.get('id', 'N/A')}")
        if len(categories["no_file"]) > 10:
            print(f"  ... 还有 {len(categories['no_file']) - 10} 个")
        
        print("\n⚠️  文件大小为0的视频:")
        for idx, (i, video) in enumerate(categories["zero_size"][:10]):
            print(f"  #{i+1}: {video.get('title', '无标题')[:60]}...")
            print(f"       观看: {video.get('numViews', 0):,} | ID: {video.get('id', 'N/A')}")
        if len(categories["zero_size"]) > 10:
            print(f"  ... 还有 {len(categories['zero_size']) - 10} 个")
        
        # 分析Gold Member视频
        if categories["gold_member"]:
            print("\n👑 Gold Member视频分析:")
            gm_with_file = sum(1 for _, v in categories["gold_member"] 
                              if v.get("file") and isinstance(v.get("file"), dict) 
                              and v["file"].get("size", 0) > 0)
            gm_without_file = len(categories["gold_member"]) - gm_with_file
            
            print(f"  总数: {len(categories['gold_member'])}")
            print(f"  有完整文件信息: {gm_with_file}")
            print(f"  缺失文件信息: {gm_without_file}")
            
            # 显示几个例子
            print("\n  示例:")
            for idx, (i, video) in enumerate(categories["gold_member"][:5]):
                file_info = video.get("file")
                if file_info and isinstance(file_info, dict):
                    size = format_size(file_info.get("size", 0))
                else:
                    size = "无文件信息"
                print(f"    {video.get('title', '无标题')[:50]}...")
                print(f"      文件: {size} | 观看: {video.get('numViews', 0):,}")
        
        return categories
        
    except Exception as e:
        print(f"错误: {e}")
        return None

def export_filtered_videos(filepath, filter_type="no_file", output_file=None):
    """导出特定类型的视频列表"""
    if output_file is None:
        output_file = f"videos_{filter_type}.json"
    
    try:
        categories = analyze_videos(filepath)
        if categories and filter_type in categories:
            filtered = categories[filter_type]
            
            # 准备导出数据
            export_data = []
            for i, video in filtered:
                export_data.append({
                    "index": i + 1,
                    "id": video.get("id"),
                    "title": video.get("title"),
                    "views": video.get("numViews"),
                    "likes": video.get("numLikes"),
                    "user": video.get("user", {}).get("name") if video.get("user") else None,
                    "file_status": "null" if video.get("file") is None else "exists",
                    "created_at": video.get("createdAt")
                })
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ 已导出 {len(export_data)} 个{filter_type}视频到: {output_file}")
            
    except Exception as e:
        print(f"导出失败: {e}")

def list_videos_without_files(filepath, show_all=False):
    """专门列出所有没有文件信息的视频"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        videos = data.get("videos", [])
        problematic = []
        
        for i, video in enumerate(videos):
            file_info = video.get("file")
            if file_info is None or (isinstance(file_info, dict) and file_info.get("size", 0) == 0):
                problematic.append((i+1, video))
        
        print(f"\n找到 {len(problematic)} 个文件信息有问题的视频:\n")
        
        # 表头
        print(f"{'序号':<6} {'标题':<50} {'观看':<8} {'点赞':<8} {'状态':<10}")
        print("-" * 90)
        
        # 显示数量限制
        show_count = len(problematic) if show_all else min(50, len(problematic))
        
        for idx, (pos, video) in enumerate(problematic[:show_count]):
            title = video.get("title", "无标题")[:47] + "..." if len(video.get("title", "")) > 50 else video.get("title", "无标题")
            views = video.get("numViews", 0)
            likes = video.get("numLikes", 0)
            
            # 判断状态
            if video.get("file") is None:
                status = "无file字段"
            elif video.get("file", {}).get("size", 0) == 0:
                status = "文件大小0"
            else:
                status = "其他问题"
            
            print(f"{pos:<6} {title:<50} {views:<8} {likes:<8} {status:<10}")
        
        if not show_all and len(problematic) > show_count:
            print(f"\n... 还有 {len(problematic) - show_count} 个视频未显示")
            print("使用 --all 参数查看全部")
            
    except Exception as e:
        print(f"错误: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("视频过滤和分析工具")
        print("\n用法:")
        print("  python filter.py [文件路径]                      # 基本分析")
        print("  python filter.py [文件路径] --list               # 列出问题视频")
        print("  python filter.py [文件路径] --list --all         # 列出所有问题视频")
        print("  python filter.py [文件路径] --export [类型]      # 导出特定类型")
        print("\n导出类型:")
        print("  no_file    - 无文件信息的视频")
        print("  zero_size  - 文件大小为0的视频")
        print("  gold_member - Gold Member视频")
        return
    
    filepath = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/iwara_data/chunk_00000.json"
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    
    # 检查命令
    if len(sys.argv) > 2:
        if sys.argv[2] == "--list":
            show_all = "--all" in sys.argv
            list_videos_without_files(filepath, show_all)
        elif sys.argv[2] == "--export":
            filter_type = sys.argv[3] if len(sys.argv) > 3 else "no_file"
            export_filtered_videos(filepath, filter_type)
    else:
        # 默认运行分析
        analyze_videos(filepath)

if __name__ == "__main__":
    main()