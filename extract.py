#!/usr/bin/env python3
"""
简单的视频JSON查看器
快速查看JSON文件中的前N个视频信息
"""

import json
import sys
from pathlib import Path

def format_size(bytes):
    """格式化文件大小"""
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes/1024:.1f} KB"
    elif bytes < 1024 * 1024 * 1024:
        return f"{bytes/1024/1024:.1f} MB"
    else:
        return f"{bytes/1024/1024/1024:.1f} GB"

def view_videos(filepath, num_videos=200):
    """查看前N个视频的基本信息"""
    file_path = Path(filepath)
    
    if not file_path.exists():
        print(f"错误：文件不存在 - {filepath}")
        return
    
    print(f"读取文件: {filepath}")
    print("=" * 100)
    
    try:
        # 尝试作为完整JSON读取
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "videos" in data:
            videos = data["videos"]
            total = len(videos)
            show_count = min(num_videos, total)
            
            print(f"文件包含 {total} 个视频，显示前 {show_count} 个：\n")
            
            # 表头
            print(f"{'序号':<6} {'标题':<50} {'观看':<8} {'点赞':<8} {'大小':<10} {'时长':<8}")
            print("-" * 100)
            
            # 显示视频列表
            for i, video in enumerate(videos[:show_count], 1):
                try:
                    title = video.get("title", "无标题")[:47] + "..." if len(video.get("title", "")) > 50 else video.get("title", "无标题")
                    views = video.get("numViews", 0)
                    likes = video.get("numLikes", 0)
                    
                    # 安全获取file_info
                    file_info = video.get("file") if video.get("file") is not None else {}
                    size = format_size(file_info.get("size", 0) if isinstance(file_info, dict) else 0)
                    duration = file_info.get("duration", 0) if isinstance(file_info, dict) else 0
                    
                    # 格式化时长
                    if duration > 0:
                        mins = duration // 60
                        secs = duration % 60
                        duration_str = f"{mins}:{secs:02d}"
                    else:
                        duration_str = "N/A"
                    
                    print(f"{i:<6} {title:<50} {views:<8} {likes:<8} {size:<10} {duration_str:<8}")
                    
                except Exception as e:
                    # 如果某个视频出错，显示错误信息但继续处理
                    print(f"{i:<6} [错误: {str(e)}]")
                    if "--debug" in sys.argv:
                        print(f"       问题视频数据: {video}")
                
                # 每20行加一个分隔线
                if i % 20 == 0 and i < show_count:
                    print("-" * 100)
            
            # 统计信息
            print("\n" + "=" * 100)
            print("📊 快速统计:")
            
            # 安全计算总大小
            total_size = 0
            for v in videos:
                file_info = v.get("file") if v.get("file") is not None else {}
                if isinstance(file_info, dict):
                    total_size += file_info.get("size", 0)
            
            total_views = sum(v.get("numViews", 0) for v in videos)
            avg_views = total_views / total if total > 0 else 0
            
            print(f"  总视频数: {total}")
            print(f"  总大小: {format_size(total_size)}")
            print(f"  总观看数: {total_views:,}")
            print(f"  平均观看数: {avg_views:,.0f}")
            
        else:
            print("文件格式不符合预期")
            
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        print("\n尝试读取文件的前1000个字符...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(1000)
            print(content)
            if len(content) == 1000:
                print("\n... (文件内容已截断)")
                
    except Exception as e:
        print(f"发生错误: {e}")

def search_videos(filepath, keyword):
    """搜索包含关键词的视频"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "videos" in data:
            videos = data["videos"]
            results = []
            
            # 搜索标题包含关键词的视频
            for video in videos:
                title = video.get("title", "")
                if keyword.lower() in title.lower():
                    results.append(video)
            
            print(f"\n搜索 '{keyword}' 找到 {len(results)} 个结果：\n")
            
            for i, video in enumerate(results[:50], 1):  # 最多显示50个结果
                print(f"{i}. {video.get('title', '无标题')}")
                print(f"   观看: {video.get('numViews', 0):,} | 点赞: {video.get('numLikes', 0):,}")
                print(f"   ID: {video.get('id', 'N/A')}")
                print()
                
    except Exception as e:
        print(f"搜索时出错: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("简单视频JSON查看器")
        print("\n用法:")
        print("  python view.py [文件路径] [显示数量]")
        print("  python view.py [文件路径] --search [关键词]")
        print("\n示例:")
        print("  python view.py videos.json 50")
        print("  python view.py videos.json --search 母狗")
        return
    
    # 默认参数
    filepath = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/iwara_data/chunk_00000.json"
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    
    # 检查是否是搜索模式
    if len(sys.argv) > 2 and sys.argv[2] == "--search":
        keyword = sys.argv[3] if len(sys.argv) > 3 else ""
        if keyword:
            search_videos(filepath, keyword)
        else:
            print("请提供搜索关键词")
    else:
        # 显示模式
        num_videos = 200
        if len(sys.argv) > 2:
            try:
                num_videos = int(sys.argv[2])
            except ValueError:
                print(f"警告：无效的数量参数，使用默认值 {num_videos}")
        
        view_videos(filepath, num_videos)

if __name__ == "__main__":
    main()