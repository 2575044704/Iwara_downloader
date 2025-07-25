./calculate.py                                                                                      0000644 0000000 0000000 00000013014 15022602700 012211  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
"""
统计所有chunk文件中视频的总大小
精确到MB
"""

import json
import sys
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

def bytes_to_mb(bytes_value):
    """将字节转换为MB，保留2位小数"""
    mb = Decimal(bytes_value) / Decimal(1024 * 1024)
    return mb.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def bytes_to_human(bytes_value):
    """将字节转换为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def calculate_chunk_size(chunk_file):
    """计算单个chunk文件中所有视频的总大小"""
    try:
        with open(chunk_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or "videos" not in data:
            print(f"  ⚠️  {chunk_file.name} 格式错误")
            return 0, 0
        
        videos = data["videos"]
        total_size = 0
        video_count = 0
        
        for video in videos:
            file_info = video.get("file")
            if file_info and isinstance(file_info, dict):
                size = file_info.get("size", 0)
                if size > 0:
                    total_size += size
                    video_count += 1
        
        return total_size, video_count
        
    except Exception as e:
        print(f"  ❌ 读取 {chunk_file.name} 失败: {e}")
        return 0, 0

def calculate_total_size(directory):
    """计算目录中所有chunk文件的视频总大小"""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"错误：目录不存在 - {directory}")
        return
    
    # 找到所有chunk文件
    chunk_files = sorted(dir_path.glob("chunk_*.json"))
    
    if not chunk_files:
        print(f"错误：在 {directory} 中没有找到chunk文件")
        return
    
    print(f"找到 {len(chunk_files)} 个chunk文件")
    print("=" * 80)
    
    # 统计变量
    grand_total_bytes = 0
    grand_total_videos = 0
    chunk_stats = []
    
    # 处理每个文件
    print("正在计算...")
    for i, chunk_file in enumerate(chunk_files):
        chunk_size, video_count = calculate_chunk_size(chunk_file)
        grand_total_bytes += chunk_size
        grand_total_videos += video_count
        
        chunk_stats.append({
            "name": chunk_file.name,
            "size": chunk_size,
            "size_mb": float(bytes_to_mb(chunk_size)),
            "videos": video_count
        })
        
        # 显示进度
        print(f"  [{i+1}/{len(chunk_files)}] {chunk_file.name}: "
              f"{video_count} 个视频, {bytes_to_human(chunk_size)}")
    
    # 显示详细统计
    print("\n" + "=" * 80)
    print("📊 详细统计:")
    print(f"{'文件名':<20} {'视频数':>8} {'大小(MB)':>15} {'大小(GB)':>12}")
    print("-" * 60)
    
    for stat in chunk_stats:
        gb_size = stat["size_mb"] / 1024
        print(f"{stat['name']:<20} {stat['videos']:>8} {stat['size_mb']:>15,.2f} {gb_size:>12,.2f}")
    
    # 显示总计
    print("-" * 60)
    total_mb = float(bytes_to_mb(grand_total_bytes))
    total_gb = total_mb / 1024
    total_tb = total_gb / 1024
    
    print(f"{'总计':<20} {grand_total_videos:>8} {total_mb:>15,.2f} {total_gb:>12,.2f}")
    
    # 显示汇总
    print("\n" + "=" * 80)
    print("📈 汇总信息:")
    print(f"  文件数量: {len(chunk_files)} 个")
    print(f"  视频总数: {grand_total_videos:,} 个")
    print(f"  平均每个文件: {grand_total_videos/len(chunk_files):.0f} 个视频")
    print(f"\n  总大小统计:")
    print(f"    字节(Bytes): {grand_total_bytes:,}")
    print(f"    兆字节(MB): {total_mb:,.2f}")
    print(f"    吉字节(GB): {total_gb:,.2f}")
    print(f"    太字节(TB): {total_tb:,.2f}")
    
    # 计算平均值
    if grand_total_videos > 0:
        avg_size_bytes = grand_total_bytes / grand_total_videos
        avg_size_mb = float(bytes_to_mb(avg_size_bytes))
        print(f"\n  平均每个视频:")
        print(f"    大小: {bytes_to_human(avg_size_bytes)} ({avg_size_mb:.2f} MB)")
    
    # 保存统计报告
    report = {
        "directory": str(dir_path),
        "chunk_files": len(chunk_files),
        "total_videos": grand_total_videos,
        "total_size": {
            "bytes": grand_total_bytes,
            "mb": total_mb,
            "gb": total_gb,
            "tb": total_tb
        },
        "average_per_video": {
            "bytes": int(avg_size_bytes) if grand_total_videos > 0 else 0,
            "mb": avg_size_mb if grand_total_videos > 0 else 0
        },
        "chunk_details": chunk_stats
    }
    
    report_path = dir_path / "size_statistics.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 统计报告已保存到: {report_path}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("统计所有视频总大小")
        print("\n用法:")
        print("  python calculate_size.py [目录路径]")
        print("\n示例:")
        print("  python calculate_size.py /iwara_data_pured")
        return
    
    # 默认路径
    directory = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/iwara_data_pured"
    
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    
    print(f"统计目录: {directory}")
    calculate_total_size(directory)

if __name__ == "__main__":
    main()                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    ./extract.py                                                                                        0000644 0000000 0000000 00000014735 15022577217 011757  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
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
    main()                                   ./fliter.py                                                                                         0000644 0000000 0000000 00000022555 15022577447 011576  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
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
    main()                                                                                                                                                   ./hfupload.py                                                                                       0000644 0000000 0000000 00000004052 15023026026 012062  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   from pathlib import Path
from huggingface_hub import HfApi, login
from concurrent.futures import ThreadPoolExecutor, as_completed

repo_id = 'ACCA225/iwara_metadata'
yun_folders = ['./upload']

def hugface_upload(yun_folders, repo_id):
    hugToken = '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'
    if hugToken != '':
        login(token=hugToken)
        api = HfApi()
        print("HfApi 类已实例化")
        print("开始上传文件...")
        
        # 任务列表
        upload_tasks = []

        # 创建一个线程池
        with ThreadPoolExecutor(max_workers=15) as executor:  # 设置最大线程数
            for yun_folder in yun_folders:
                folder_path = Path(yun_folder)
                if folder_path.exists() and folder_path.is_dir():
                    for file_in_folder in folder_path.glob('**/*'):
                        if file_in_folder.is_file():
                            # 提交上传任务到线程池
                            task = executor.submit(upload_file, api, file_in_folder, folder_path, repo_id)
                            upload_tasks.append(task)
                else:
                    print(f'Error: Folder {yun_folder} does not exist')

            # 等待所有线程完成并获取结果
            for task in as_completed(upload_tasks):
                try:
                    response = task.result()
                    print("文件上传完成")
                    print(f"响应: {response}")
                except Exception as e:
                    print(f"上传失败: {e}")

    else:
        print(f'Error: Token is empty')

def upload_file(api, file_in_folder, folder_path, repo_id):
    try:
        response = api.upload_file(
            path_or_fileobj=file_in_folder,
            path_in_repo=str(file_in_folder.relative_to(folder_path.parent)),
            repo_id=repo_id,
            repo_type="dataset"
        )
        return response
    except Exception as e:
        print(f"文件 {file_in_folder} 上传失败: {e}")
        return None

hugface_upload(yun_folders, repo_id)
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      ./iwara.py                                                                                          0000644 0000000 0000000 00000045033 15022171137 011372  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
"""
Iwara 高速爬虫 - 优化版本
主要优化：
1. 增量保存机制，避免重复序列化已保存的数据
2. 异步保存，不阻塞主线程
3. 内存管理优化，定期清理已保存的数据
4. 使用更高效的数据结构
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import os
import glob
from typing import List, Dict, Optional, Set
import signal
import sys
import threading
from collections import deque

# 配置
TOKEN_PRIMARY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjdiM2I5MDk4LWViMjEtNGIzOC04Y2VhLTc1ZGMzM2FmMjY1YyIsInR5cGUiOiJhY2Nlc3NfdG9rZW4iLCJyb2xlIjoidXNlciIsInByZW1pdW0iOmZhbHNlLCJpc3MiOiJpd2FyYSIsImlhdCI6MTc0OTMxMzQ1MiwiZXhwIjoxNzQ5MzE3MDUyfQ.TUPlMeLik17ratOMy7XWY1aK6UeuAJoETzf2x-CsQOE"
TOKEN_BACKUP = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjA1NDVjYmNmLThkNGEtNDMxOS1iYzQ1LTVjMDJlMTNmMjIwOCIsInR5cGUiOiJhY2Nlc3NfdG9rZW4iLCJyb2xlIjoibGltaXRlZCIsInByZW1pdW0iOmZhbHNlLCJpc3MiOiJpd2FyYSIsImlhdCI6MTc0OTMxMjg3OSwiZXhwIjoxNzQ5MzE2NDc5fQ.k4sS9TKVjfv4vAmLo5njfX5MCJ4zst_JKgY2TP3RIwo"
START_PAGE = 1
END_PAGE = 8210
OUTPUT_DIR = "iwara_data"  # 使用目录存储多个文件
CONCURRENT_REQUESTS = 50
BATCH_SIZE = 100
SAVE_INTERVAL = 180  # 3分钟
SAVE_EVERY_N_PAGES = 500
MEMORY_CLEAR_THRESHOLD = 1000  # 每1000页清理一次内存

class OptimizedIwaraScraper:
    def __init__(self, resume_from: Optional[Dict] = None):
        # 创建输出目录
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Token管理
        self.tokens = {
            'primary': TOKEN_PRIMARY,
            'backup': TOKEN_BACKUP
        }
        self.current_token = 'primary'
        self.token_failures = {'primary': 0, 'backup': 0}
        
        self.headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {self.tokens[self.current_token]}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 使用更高效的数据结构
        self.pending_videos = deque()  # 待保存的视频队列
        self.pending_pages = deque()   # 待保存的页面数据队列
        self.completed_pages: Set[int] = set()  # 已完成的页面集合
        self.failed_pages: List[int] = []
        
        # 统计信息
        self.total_videos_saved = 0
        self.total_pages_saved = 0
        self.success_count = 0
        self.chunk_counter = 0  # 用于生成唯一的文件名
        
        # 从检查点恢复
        if resume_from:
            self._restore_from_checkpoint(resume_from)
        
        # 时间管理
        self.start_time = time.time()
        self.last_save_time = time.time()
        self.last_save_count = 0
        self.consecutive_failures = 0
        self.is_shutting_down = False
        
        # 保存锁，防止并发保存
        self.save_lock = asyncio.Lock()
        self.is_saving = False
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _restore_from_checkpoint(self, checkpoint: Dict):
        """从检查点恢复状态"""
        print("📥 从检查点恢复数据...")
        metadata = checkpoint.get('metadata', {})
        
        self.completed_pages = set(metadata.get('completed_pages', []))
        self.failed_pages = metadata.get('failed_pages', [])
        self.total_videos_saved = metadata.get('total_videos_saved', 0)
        self.total_pages_saved = metadata.get('total_pages_saved', 0)
        self.success_count = metadata.get('success_count', 0)
        self.chunk_counter = metadata.get('chunk_counter', 0)
        
        print(f"   已恢复状态: {self.total_videos_saved} 个视频已保存, "
              f"{self.success_count} 个页面已完成")
    
    def _switch_token(self):
        """切换到备用Token"""
        old_token = self.current_token
        self.current_token = 'backup' if self.current_token == 'primary' else 'primary'
        self.headers['authorization'] = f'Bearer {self.tokens[self.current_token]}'
        print(f"🔄 切换Token: {old_token} → {self.current_token}")
    
    def _signal_handler(self, signum, frame):
        """处理中断信号"""
        if not self.is_shutting_down:
            self.is_shutting_down = True
            print("\n\n🛑 收到中断信号，正在保存数据...")
            # 使用线程执行同步保存，避免在信号处理器中使用异步
            save_thread = threading.Thread(target=self._emergency_save_sync)
            save_thread.start()
            save_thread.join(timeout=30)  # 最多等待30秒
            sys.exit(0)
    
    def _emergency_save_sync(self):
        """同步的紧急保存"""
        try:
            # 保存待处理的数据
            if self.pending_videos or self.pending_pages:
                filename = os.path.join(OUTPUT_DIR, f"emergency_chunk_{int(time.time())}.json")
                self._save_chunk_sync(filename, list(self.pending_videos), list(self.pending_pages))
            
            # 保存元数据
            self._save_metadata_sync(is_emergency=True)
            print("✅ 紧急保存完成")
        except Exception as e:
            print(f"❌ 紧急保存失败: {e}")
    
    async def fetch_page(self, session: aiohttp.ClientSession, page: int, 
                        retry_count: int = 0, token_switched: bool = False) -> Optional[Dict]:
        """获取单页数据"""
        if page in self.completed_pages:
            return None
        
        url = f"https://api.iwara.tv/videos?rating=all&sort=date&page={page}"
        max_retries = 3
        
        try:
            async with session.get(url, headers=self.headers, timeout=20) as response:
                if response.status == 200:
                    data = await response.json()
                    self.success_count += 1
                    self.completed_pages.add(page)
                    self.consecutive_failures = 0
                    self.token_failures[self.current_token] = 0
                    
                    # 显示进度
                    if self.success_count % 50 == 0:
                        await self._show_progress()
                    
                    return {'page': page, 'data': data}
                
                elif response.status == 429:  # 限流
                    self.token_failures[self.current_token] += 1
                    
                    if not token_switched and self.token_failures[self.current_token] > 5:
                        self._switch_token()
                        return await self.fetch_page(session, page, retry_count, True)
                    
                    wait_time = min(10 * (retry_count + 1), 60)
                    print(f"⚠️ 页面 {page} 限流，等待 {wait_time}秒...")
                    await asyncio.sleep(wait_time)
                    
                    if retry_count < max_retries:
                        return await self.fetch_page(session, page, retry_count + 1, token_switched)
                
                elif response.status == 401:  # Token无效
                    if not token_switched:
                        self._switch_token()
                        return await self.fetch_page(session, page, 0, True)
                    else:
                        print("❌ 两个Token都已失效！")
                        self.is_shutting_down = True
                        return None
                
                else:
                    if retry_count < max_retries:
                        await asyncio.sleep(2 ** retry_count)
                        return await self.fetch_page(session, page, retry_count + 1, token_switched)
            
            self.failed_pages.append(page)
            self.consecutive_failures += 1
            return None
            
        except Exception as e:
            if retry_count < max_retries:
                await asyncio.sleep(3)
                return await self.fetch_page(session, page, retry_count + 1, token_switched)
            
            print(f"❌ 页面 {page} 失败: {type(e).__name__}")
            self.failed_pages.append(page)
            self.consecutive_failures += 1
            return None
    
    async def _show_progress(self):
        """显示进度信息"""
        elapsed = time.time() - self.start_time
        rate = self.success_count / elapsed if elapsed > 0 else 0
        remaining = END_PAGE - START_PAGE - self.success_count
        eta = remaining / rate if rate > 0 else 0
        
        # 计算内存中待保存的数据量
        pending_count = len(self.pending_videos) + len(self.pending_pages)
        
        print(f"📊 进度: {self.success_count}/{END_PAGE-START_PAGE+1} "
              f"速率: {rate:.1f}页/秒 剩余: {eta/60:.1f}分钟 "
              f"已保存: {self.total_videos_saved}视频 "
              f"待保存: {pending_count}项")
    
    async def process_batch(self, session: aiohttp.ClientSession, pages: List[int]):
        """处理一批页面"""
        tasks = [self.fetch_page(session, page) for page in pages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict) and result:
                # 添加到待保存队列，而不是立即存储在内存中
                page_data = {
                    'page': result['page'],
                    'timestamp': datetime.now().isoformat(),
                    'data': result['data']
                }
                self.pending_pages.append(page_data)
                
                # 提取视频并添加到待保存队列
                videos = result['data'].get('results', [])
                for video in videos:
                    video_copy = video.copy()
                    video_copy['_page'] = result['page']
                    video_copy['_fetchTime'] = datetime.now().isoformat()
                    self.pending_videos.append(video_copy)
    
    async def _save_chunk_async(self):
        """异步保存数据块"""
        if self.is_saving or (not self.pending_videos and not self.pending_pages):
            return
        
        async with self.save_lock:
            self.is_saving = True
            
            # 获取要保存的数据
            videos_to_save = list(self.pending_videos)
            pages_to_save = list(self.pending_pages)
            
            # 清空待保存队列
            self.pending_videos.clear()
            self.pending_pages.clear()
            
            # 在后台线程中执行保存
            loop = asyncio.get_event_loop()
            filename = os.path.join(OUTPUT_DIR, f"chunk_{self.chunk_counter:05d}.json")
            
            try:
                await loop.run_in_executor(
                    None, 
                    self._save_chunk_sync, 
                    filename, 
                    videos_to_save, 
                    pages_to_save
                )
                
                self.chunk_counter += 1
                self.total_videos_saved += len(videos_to_save)
                self.total_pages_saved += len(pages_to_save)
                
                # 保存元数据
                await loop.run_in_executor(None, self._save_metadata_sync, False)
                
                print(f"💾 保存数据块 {filename}: {len(videos_to_save)} 个视频")
                
            except Exception as e:
                print(f"❌ 保存失败: {e}")
                # 恢复数据到队列
                self.pending_videos.extend(videos_to_save)
                self.pending_pages.extend(pages_to_save)
            
            finally:
                self.is_saving = False
    
    def _save_chunk_sync(self, filename: str, videos: List[Dict], pages: List[Dict]):
        """同步保存数据块"""
        data = {
            'videos': videos,
            'pages': pages,
            'metadata': {
                'chunk_id': self.chunk_counter,
                'timestamp': datetime.now().isoformat(),
                'video_count': len(videos),
                'page_count': len(pages)
            }
        }
        
        # 普通JSON保存
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    
    def _save_metadata_sync(self, is_emergency: bool = False):
        """保存元数据"""
        metadata = {
            'total_videos_saved': self.total_videos_saved,
            'total_pages_saved': self.total_pages_saved,
            'success_count': self.success_count,
            'completed_pages': sorted(list(self.completed_pages)),
            'failed_pages': sorted(list(set(self.failed_pages))),
            'chunk_counter': self.chunk_counter,
            'duration_seconds': time.time() - self.start_time,
            'save_time': datetime.now().isoformat(),
            'is_emergency': is_emergency,
            'current_token': self.current_token,
            'token_failures': self.token_failures
        }
        
        filename = os.path.join(OUTPUT_DIR, 'metadata.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def should_save(self) -> bool:
        """判断是否需要保存"""
        time_since_save = time.time() - self.last_save_time
        pages_since_save = self.success_count - self.last_save_count
        
        return (time_since_save >= SAVE_INTERVAL or
                pages_since_save >= SAVE_EVERY_N_PAGES or
                len(self.pending_videos) > 10000 or  # 内存压力
                self.consecutive_failures > 10)
    
    async def run(self):
        """主运行函数"""
        print("🚀 Iwara 优化爬虫启动")
        print(f"📋 目标: {START_PAGE} - {END_PAGE} (共 {END_PAGE-START_PAGE+1} 页)")
        print(f"⚙️  配置: 并发={CONCURRENT_REQUESTS}, 批次={BATCH_SIZE}")
        print(f"💾 数据保存到: {OUTPUT_DIR}/")
        print("🛑 按 Ctrl+C 安全退出并保存\n")
        
        connector = aiohttp.TCPConnector(
            limit=CONCURRENT_REQUESTS,
            force_close=True
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # 测试Token
            print("🔑 验证Token...")
            test_result = await self.fetch_page(session, START_PAGE)
            if not test_result:
                print("❌ Token无效或网络问题")
                return
            print("✅ Token有效\n")
            
            # 主循环
            all_pages = [p for p in range(START_PAGE, END_PAGE + 1)
                        if p not in self.completed_pages]
            
            for i in range(0, len(all_pages), BATCH_SIZE):
                if self.is_shutting_down:
                    break
                
                batch = all_pages[i:i + BATCH_SIZE]
                await self.process_batch(session, batch)
                
                # 检查是否需要保存
                if self.should_save():
                    await self._save_chunk_async()
                    self.last_save_time = time.time()
                    self.last_save_count = self.success_count
                
                # 动态调整速度
                if self.consecutive_failures > 5:
                    print(f"⚠️ 连续失败{self.consecutive_failures}次，减速...")
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(0.1)  # 更短的延迟
            
            # 最终保存
            if not self.is_shutting_down:
                print("\n✅ 爬取完成！正在保存最后的数据...")
                await self._save_chunk_async()
                
                # 生成最终报告
                await self._generate_final_report()
    
    async def _generate_final_report(self):
        """生成最终报告"""
        elapsed = time.time() - self.start_time
        
        report = {
            'summary': {
                'total_duration_minutes': elapsed / 60,
                'total_videos': self.total_videos_saved,
                'total_pages': self.total_pages_saved,
                'success_pages': self.success_count,
                'failed_pages': len(set(self.failed_pages)),
                'average_rate_per_second': self.success_count / elapsed if elapsed > 0 else 0,
                'data_chunks': self.chunk_counter
            },
            'failed_pages': sorted(list(set(self.failed_pages))),
            'completion_time': datetime.now().isoformat()
        }
        
        # 保存报告
        report_file = os.path.join(OUTPUT_DIR, 'final_report.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印报告
        print(f"\n📊 最终统计:")
        print(f"   总用时: {elapsed/60:.1f} 分钟")
        print(f"   成功页数: {self.success_count}")
        print(f"   失败页数: {len(set(self.failed_pages))}")
        print(f"   视频总数: {self.total_videos_saved}")
        print(f"   平均速率: {self.success_count/elapsed:.1f} 页/秒")
        print(f"   数据文件: {self.chunk_counter} 个")
        print(f"\n📁 所有数据保存在: {OUTPUT_DIR}/")

async def main():
    # 检查是否有之前的元数据
    metadata_file = os.path.join(OUTPUT_DIR, 'metadata.json')
    resume_data = None
    
    if os.path.exists(metadata_file):
        print(f"📂 发现之前的元数据: {metadata_file}")
        print("是否从此状态恢复? (y/n): ", end='')
        
        if input().strip().lower() == 'y':
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    resume_data = {'metadata': json.load(f)}
                print("✅ 状态恢复成功")
            except Exception as e:
                print(f"❌ 加载失败: {e}")
    
    scraper = OptimizedIwaraScraper(resume_from=resume_data)
    
    try:
        await scraper.run()
    except Exception as e:
        print(f"\n❌ 程序异常: {type(e).__name__}: {e}")
        scraper._emergency_save_sync()

if __name__ == "__main__":
    print("=" * 60)
    print("Iwara 高速爬虫 - 优化版本")
    print("=" * 60)
    
    # 检查依赖
    try:
        import aiohttp
    except ImportError:
        print("❌ 请先安装 aiohttp: pip install aiohttp")
        sys.exit(1)
    
    # 运行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序已退出")
    except Exception as e:
        print(f"\n致命错误: {e}")
        import traceback
        traceback.print_exc()

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     ./iwara_batch_downloader.py                                                                         0000644 0000000 0000000 00000056526 15023456145 014770  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
"""
Iwara 批量视频下载爬虫 - 集成 Playwright 版本（改进版）
自动处理 Playwright 浏览器安装问题
"""

import requests
import json
import os
import time
import glob
from pathlib import Path
import sys
import subprocess
from playwright.sync_api import sync_playwright

class IwaraBatchDownloader:
    def __init__(self, bearer_token=None):
        self.bearer_token = bearer_token
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        if bearer_token:
            self.headers['Authorization'] = f'Bearer {bearer_token}'
        self.api_base = 'https://api.iwara.tv/video/'
        self.failed_downloads = []
        self.last_playwright_error = None
        self.skip_count = 0
        
        # 检查并安装 Playwright 浏览器
        self._ensure_playwright_installed()
        
    def _ensure_playwright_installed(self):
        """确保 Playwright 浏览器已安装"""
        try:
            # 尝试启动浏览器以测试是否已安装
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
                browser.close()
            print("[Playwright] 浏览器已就绪")
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "Looks like Playwright" in str(e):
                print("[Playwright] 检测到浏览器未安装，正在自动安装...")
                try:
                    # 尝试自动安装
                    result = subprocess.run(['playwright', 'install', 'chromium'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        print("[Playwright] 浏览器安装成功！")
                        
                        # 检查是否需要安装系统依赖
                        print("[Playwright] 检查系统依赖...")
                        deps_result = subprocess.run(['playwright', 'install-deps', 'chromium'], 
                                                   capture_output=True, text=True)
                        if deps_result.returncode == 0:
                            print("[Playwright] 系统依赖安装成功")
                        else:
                            print("[Playwright] 系统依赖安装失败（可能需要 sudo 权限）")
                            print("[Playwright] 如果遇到问题，请手动运行: sudo playwright install-deps chromium")
                    else:
                        print(f"[Playwright] 自动安装失败: {result.stderr}")
                        print("[Playwright] 请手动运行以下命令：")
                        print("  playwright install chromium")
                        print("  playwright install-deps chromium  # 如果需要系统依赖")
                        sys.exit(1)
                except FileNotFoundError:
                    print("[错误] playwright 命令未找到，请确保已安装 playwright")
                    print("运行: pip install playwright")
                    sys.exit(1)
            else:
                print(f"[Playwright] 初始化错误: {e}")
                
    def get_video_info_playwright(self, video_id, retry_count=0):
        """使用 Playwright 获取视频信息，绕过反爬机制"""
        url = f"https://www.iwara.tv/video/{video_id}"
        print(f"[Playwright] 访问视频页面: {url}")
        
        error_info = None
        
        try:
            with sync_playwright() as p:
                # 添加更多启动选项以提高稳定性
                browser_args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',  # 在某些环境下需要
                    '--disable-gpu'
                ]
                
                browser = p.chromium.launch(
                    headless=True, 
                    args=browser_args,
                    timeout=60000  # 增加超时时间
                )
                
                # 创建上下文时添加更多选项
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    ignore_https_errors=True
                )
                
                page = context.new_page()
                
                result = {'found': False, 'data': None, 'error': None}
                target_pattern = "files.iwara.tv/file"
                
                def handle_response(response):
                    if target_pattern in response.url and not result['found']:
                        result['found'] = True
                        
                        try:
                            body = response.body()
                            data = json.loads(body)
                            
                            # 定义质量优先级
                            quality_priority = {
                                'source': 1,
                                '720': 2, 
                                '540': 3,
                                '360': 4,
                                'preview': 99
                            }
                            
                            # 解析并排序视频
                            videos = []
                            for item in data:
                                name_lower = item['name'].lower()
                                priority = 999
                                
                                for quality, p in quality_priority.items():
                                    if quality in name_lower:
                                        priority = p
                                        break
                                
                                videos.append({
                                    'name': item['name'],
                                    'type': item['type'],
                                    'view_url': f"https:{item['src']['view']}",
                                    'download_url': f"https:{item['src']['download']}",
                                    'priority': priority
                                })
                            
                            videos.sort(key=lambda x: x['priority'])
                            
                            if videos:
                                best_video = videos[0]
                                print(f"[Playwright] 找到最佳质量: {best_video['name']}")
                                
                                result['data'] = {
                                    'best_video': best_video,
                                    'all_videos': videos
                                }
                            else:
                                result['error'] = '响应中无可用视频'
                            
                        except Exception as e:
                            result['error'] = f'处理响应错误: {str(e)}'
                            print(f"[Playwright] 处理响应错误: {e}")
                
                page.on("response", handle_response)
                
                # 访问页面
                try:
                    page.goto(url, wait_until='commit', timeout=30000)
                    
                    # 轮询检查是否找到目标，最多等待20秒
                    for i in range(40):  # 40 * 0.5 = 20秒
                        if result['found']:
                            break
                        page.wait_for_timeout(500)  # 每次等待0.5秒
                    
                    if not result['found']:
                        error_info = '超时：未找到视频API请求'
                        
                except Exception as e:
                    error_info = f'页面访问错误: {str(e)}'
                    print(f"[Playwright] {error_info}")
                
                # 立即关闭所有资源
                page.close()
                context.close()
                browser.close()
                
                # 如果有错误，记录到结果中
                if error_info and not result['error']:
                    result['error'] = error_info
                
                # 返回数据，如果有错误则返回None，并记录错误
                if result['error']:
                    self.last_playwright_error = result['error']
                    
                    # 如果是特定错误且重试次数未超限，则重试
                    if retry_count < 2 and "Executable doesn't exist" in str(result['error']):
                        print(f"[Playwright] 检测到浏览器问题，尝试重新初始化... (重试 {retry_count + 1}/2)")
                        self._ensure_playwright_installed()
                        return self.get_video_info_playwright(video_id, retry_count + 1)
                    
                    return None
                    
                return result['data']
                
        except Exception as e:
            self.last_playwright_error = f'Playwright初始化错误: {str(e)}'
            print(f"[Playwright] {self.last_playwright_error}")
            
            # 如果是浏览器未安装的错误，尝试重新安装
            if retry_count < 2 and ("Executable doesn't exist" in str(e) or "Looks like Playwright" in str(e)):
                print(f"[Playwright] 尝试重新安装浏览器... (重试 {retry_count + 1}/2)")
                self._ensure_playwright_installed()
                return self.get_video_info_playwright(video_id, retry_count + 1)
                
            return None
    
    def download_video_aria2c(self, download_url, filename):
        """使用 aria2c 下载视频文件"""
        if download_url.startswith('//'):
            download_url = 'https:' + download_url
            
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
            
        print(f"[下载URL] {download_url}")
        print(f"[保存路径] {filename}")
        
        # 构建 aria2c 命令
        cmd = [
            'aria2c',
            download_url,
            '-o', filename,
            '-x', '16',
            '-s', '16',
            '-c',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--header=Accept: video/mp4,video/*;q=0.9,*/*;q=0.8',
            '--header=Referer: https://www.iwara.tv/',
            '--check-certificate=false',
            '--timeout=20',
            '--connect-timeout=10',
            '--max-tries=1',
            '--lowest-speed-limit=1K',
            '--summary-interval=5',
            '--console-log-level=warn'
        ]
        
        print(f"[执行命令] aria2c (尝试下载)")
        
        try:
            result = subprocess.run(cmd, timeout=60)
            
            if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"[完成] {os.path.basename(filename)}")
                return True
            else:
                print(f"[失败] aria2c 无法下载，切换到 curl")
                
        except subprocess.TimeoutExpired:
            print(f"[超时] aria2c 超时，切换到 curl")
            try:
                subprocess.run(['pkill', '-f', f'aria2c.*{os.path.basename(filename)}'], capture_output=True)
            except:
                pass
                
        except Exception as e:
            print(f"[错误] aria2c 失败: {e}")
            
        # 清理残留文件
        if os.path.exists(filename + '.aria2'):
            os.remove(filename + '.aria2')
        if os.path.exists(filename) and os.path.getsize(filename) == 0:
            os.remove(filename)
            
        return self.download_video_curl(download_url, filename)
        
    def download_video_curl(self, download_url, filename):
        """使用 curl 下载"""
        print(f"[curl] 开始下载 {os.path.basename(filename)}")
        
        cmd = [
            'curl',
            '-L',
            '-o', filename,
            '-C', '-',
            '--connect-timeout', '3',
            '--max-time', '30',
            '--retry', '1',
            '--retry-delay', '5',
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '-H', 'Accept: video/mp4,video/*;q=0.9,*/*;q=0.8',
            '-H', 'Referer: https://www.iwara.tv/',
            '--compressed',
            '--insecure',
            download_url
        ]
        
        try:
            print("[curl] 下载中...")
            result = subprocess.run(cmd)
            
            if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"[完成] {os.path.basename(filename)} ✓")
                return True
            else:
                print(f"[错误] curl 下载失败，返回码: {result.returncode}")
                return self.download_video_wget(download_url, filename)
                
        except FileNotFoundError:
            print("[错误] curl 未安装，尝试 wget")
            return self.download_video_wget(download_url, filename)
        except Exception as e:
            print(f"[错误] curl 失败: {e}")
            return self.download_video_wget(download_url, filename)
            
    def download_video_wget(self, download_url, filename):
        """使用 wget 作为最终备选"""
        print(f"[wget] 最终尝试下载")
        
        cmd = [
            'wget',
            '-O', filename,
            '-c',
            '--timeout=10',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--header=Accept: video/mp4,video/*;q=0.9,*/*;q=0.8',
            '--header=Referer: https://www.iwara.tv/',
            '--no-check-certificate',
            download_url
        ]
        
        try:
            result = subprocess.run(cmd)
            
            if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"[完成] {os.path.basename(filename)} (wget) ✓")
                return True
            else:
                print(f"[错误] 所有下载方式都失败了")
                return False
                
        except Exception as e:
            print(f"[错误] wget 失败: {e}")
            return False
            
    def process_video(self, video_id, json_filename, save_dir='downloads'):
        """处理单个视频 - 使用 Playwright 获取视频信息"""
        # 重置错误信息
        self.last_playwright_error = None
        
        # 使用 Playwright 获取视频信息
        video_data = self.get_video_info_playwright(video_id)
        
        if not video_data:
            error_reason = self.last_playwright_error or 'Playwright 获取视频信息失败（未知原因）'
            self.failed_downloads.append({
                'id': video_id,
                'json_file': json_filename,
                'reason': error_reason,
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            print(f"[错误] {error_reason}")
            return False
            
        # 获取最佳质量的视频
        best_video = video_data.get('best_video')
        if not best_video:
            self.failed_downloads.append({
                'id': video_id,
                'json_file': json_filename,
                'reason': '无可用视频质量',
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return False
            
        print(f"[选择质量] {best_video['name']}")
        
        # 获取下载URL
        download_url = best_video.get('download_url')
        if not download_url:
            self.failed_downloads.append({
                'id': video_id,
                'json_file': json_filename,
                'reason': '视频无下载链接',
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return False
            
        # 使用与JSON文件相同的文件名（去掉.json后缀，加上.mp4）
        base_name = os.path.splitext(os.path.basename(json_filename))[0]
        filename = os.path.join(save_dir, f"{base_name}.mp4")
        
        # 下载视频
        success = self.download_video_aria2c(download_url, filename)
        
        if not success:
            self.failed_downloads.append({
                'id': video_id,
                'json_file': json_filename,
                'reason': '下载失败（网络或文件问题）',
                'download_url': download_url,
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        return success
        
    def process_json_file(self, json_path, save_dir='downloads'):
        """处理单个 JSON 文件"""
        try:
            # 先检查对应的MP4文件是否已存在
            base_name = os.path.splitext(os.path.basename(json_path))[0]
            mp4_filename = os.path.join(save_dir, f"{base_name}.mp4")
            
            if os.path.exists(mp4_filename) and os.path.getsize(mp4_filename) > 0:
                print(f"[跳过] 文件已存在: {base_name}.mp4")
                self.skip_count += 1
                return True  # 返回True表示"成功"（已存在）
            
            # 读取JSON文件
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            video_id = data.get('id')
            if not video_id:
                print(f"[警告] JSON 文件无 ID: {json_path}")
                self.failed_downloads.append({
                    'json_file': json_path,
                    'reason': 'JSON文件中无视频ID',
                    'time': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                return False
                
            print(f"\n[处理] {os.path.basename(json_path)}")
            
            return self.process_video(video_id, json_path, save_dir)
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析错误: {e}"
            print(f"[错误] {error_msg} - {json_path}")
            self.failed_downloads.append({
                'json_file': json_path,
                'reason': error_msg,
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return False
        except Exception as e:
            error_msg = f"读取文件错误: {str(e)}"
            print(f"[错误] {error_msg} - {json_path}")
            self.failed_downloads.append({
                'json_file': json_path,
                'reason': error_msg,
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return False
            
    def process_directory(self, directory_path, save_dir='downloads'):
        """处理整个目录的 JSON 文件"""
        json_files = glob.glob(os.path.join(directory_path, '*.json'))
        total = len(json_files)
        
        if total == 0:
            print(f"[警告] 目录中没有 JSON 文件: {directory_path}")
            return
            
        print(f"[信息] 找到 {total} 个 JSON 文件")
        print(f"[信息] 源目录: {directory_path}")
        
        # 自动创建保存目录
        os.makedirs(save_dir, exist_ok=True)
        abs_save_dir = os.path.abspath(save_dir)
        print(f"[信息] 保存目录: {abs_save_dir}")
        
        # 清理未完成的下载
        print("\n[清理] 检查未完成的下载...")
        aria2_files = glob.glob(os.path.join(save_dir, '*.aria2'))
        if aria2_files:
            print(f"[清理] 发现 {len(aria2_files)} 个未完成的下载")
            for aria2_file in aria2_files:
                os.remove(aria2_file)
                print(f"[清理] 删除: {os.path.basename(aria2_file)}")
                
                video_file = aria2_file.replace('.aria2', '')
                if os.path.exists(video_file):
                    os.remove(video_file)
                    print(f"[清理] 删除: {os.path.basename(video_file)}")
        else:
            print("[清理] 没有发现未完成的下载")
        
        # 重置计数器
        self.skip_count = 0
        success_count = 0
        
        for i, json_file in enumerate(json_files, 1):
            print(f"\n========== 进度: {i}/{total} ==========")
            result = self.process_json_file(json_file, save_dir)
            if result:
                success_count += 1
            
        # 计算真正下载的数量
        download_count = success_count - self.skip_count
        
        # 输出统计
        print(f"\n========== 完成 ==========")
        print(f"总计: {total} 个文件")
        print(f"成功: {success_count} 个")
        print(f"  - 已存在(跳过): {self.skip_count} 个")
        print(f"  - 新下载: {download_count} 个")
        print(f"失败: {total - success_count} 个")
        print(f"视频保存在: {abs_save_dir}")
        
        # 保存失败记录
        if self.failed_downloads:
            failed_file = os.path.join(save_dir, 'failed_downloads.json')
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_downloads, f, ensure_ascii=False, indent=2)
            print(f"\n失败记录已保存到: {failed_file}")
            
            # 打印失败摘要
            print("\n失败摘要:")
            error_counts = {}
            for fail in self.failed_downloads:
                reason = fail.get('reason', '未知原因')
                error_counts[reason] = error_counts.get(reason, 0) + 1
            
            for reason, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {reason}: {count} 个")

def main():
    # 创建下载器（不需要 bearer_token，因为使用 Playwright）
    downloader = IwaraBatchDownloader()
    
    # 默认下载目录
    save_dir = 'downloads'
    
    # 处理选项
    if len(sys.argv) > 1:
        path = sys.argv[1]
        
        # 如果有第二个参数，作为保存目录
        if len(sys.argv) > 2:
            save_dir = sys.argv[2]
            
        if os.path.isfile(path) and path.endswith('.json'):
            # 处理单个文件
            downloader.process_json_file(path, save_dir)
        elif os.path.isdir(path):
            # 处理整个目录
            downloader.process_directory(path, save_dir)
        else:
            print(f"[错误] 无效路径: {path}")
    else:
        # 默认处理当前目录下的 2025-06 文件夹
        default_dir = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/classification/2025-06"
        if os.path.exists(default_dir):
            downloader.process_directory(default_dir, save_dir)
        else:
            print("用法:")
            print("  python script.py <json文件或目录路径> [保存目录]")
            print("")
            print("示例:")
            print("  python script.py ./video.json")
            print("  python script.py ./video.json /path/to/save")
            print("  python script.py /path/to/json/directory")
            print("  python script.py /path/to/json/directory /path/to/save")

if __name__ == "__main__":
    main()                                                                                                                                                                          ./json_classification.py                                                                            0000644 0000000 0000000 00000020131 15023464522 014307  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
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
    main()                                                                                                                                                                                                                                                                                                                                                                                                                                       ./playwrite.py                                                                                      0000644 0000000 0000000 00000047361 15023210272 012310  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
"""
Iwara 批量视频下载爬虫 - 集成 Playwright 版本
使用 Playwright 绕过反爬机制，获取最高清 source 质量

使用方法：
# 处理单个 JSON 文件（默认保存到 ./downloads）
python iwara_batch_downloader.py "./（新）ワカメちゃん化五月雨でSmartパンツカメラ.json"

# 处理单个 JSON 文件并指定保存目录
python iwara_batch_downloader.py "./video.json" "/root/videos"

# 处理整个目录（默认保存到 ./downloads）
python iwara_batch_downloader.py /__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/classification/2025-06

# 处理整个目录并指定保存目录
python iwara_batch_downloader.py /data2/classification/2025-06 2025-06

# 使用默认目录（2025-06）
python iwara_batch_downloader.py
"""

import requests
import json
import os
import time
import glob
from pathlib import Path
import sys
import subprocess
from playwright.sync_api import sync_playwright

class IwaraBatchDownloader:
    def __init__(self, bearer_token=None):
        self.bearer_token = bearer_token
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        if bearer_token:
            self.headers['Authorization'] = f'Bearer {bearer_token}'
        self.api_base = 'https://api.iwara.tv/video/'
        self.failed_downloads = []
        self.last_playwright_error = None
        self.skip_count = 0
        
    def get_video_info_playwright(self, video_id):
        """使用 Playwright 获取视频信息，绕过反爬机制"""
        url = f"https://www.iwara.tv/video/{video_id}"
        print(f"[Playwright] 访问视频页面: {url}")
        
        error_info = None
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
                context = browser.new_context()
                page = context.new_page()
                
                result = {'found': False, 'data': None, 'error': None}
                target_pattern = "files.iwara.tv/file"
                
                def handle_response(response):
                    if target_pattern in response.url and not result['found']:
                        result['found'] = True
                        
                        try:
                            body = response.body()
                            data = json.loads(body)
                            
                            # 定义质量优先级
                            quality_priority = {
                                'source': 1,
                                '720': 2, 
                                '540': 3,
                                '360': 4,
                                'preview': 99
                            }
                            
                            # 解析并排序视频
                            videos = []
                            for item in data:
                                name_lower = item['name'].lower()
                                priority = 999
                                
                                for quality, p in quality_priority.items():
                                    if quality in name_lower:
                                        priority = p
                                        break
                                
                                videos.append({
                                    'name': item['name'],
                                    'type': item['type'],
                                    'view_url': f"https:{item['src']['view']}",
                                    'download_url': f"https:{item['src']['download']}",
                                    'priority': priority
                                })
                            
                            videos.sort(key=lambda x: x['priority'])
                            
                            if videos:
                                best_video = videos[0]
                                print(f"[Playwright] 找到最佳质量: {best_video['name']}")
                                
                                result['data'] = {
                                    'best_video': best_video,
                                    'all_videos': videos
                                }
                            else:
                                result['error'] = '响应中无可用视频'
                            
                        except Exception as e:
                            result['error'] = f'处理响应错误: {str(e)}'
                            print(f"[Playwright] 处理响应错误: {e}")
                
                page.on("response", handle_response)
                
                # 访问页面
                try:
                    page.goto(url, wait_until='commit', timeout=30000)
                    
                    # 轮询检查是否找到目标，最多等待20秒
                    for i in range(40):  # 40 * 0.5 = 20秒
                        if result['found']:
                            break
                        page.wait_for_timeout(500)  # 每次等待0.5秒
                    
                    if not result['found']:
                        error_info = '超时：未找到视频API请求'
                        
                except Exception as e:
                    error_info = f'页面访问错误: {str(e)}'
                    print(f"[Playwright] {error_info}")
                
                # 立即关闭所有资源
                page.close()
                context.close()
                browser.close()
                
                # 如果有错误，记录到结果中
                if error_info and not result['error']:
                    result['error'] = error_info
                
                # 返回数据，如果有错误则返回None，并记录错误
                if result['error']:
                    self.last_playwright_error = result['error']
                    return None
                    
                return result['data']
                
        except Exception as e:
            self.last_playwright_error = f'Playwright初始化错误: {str(e)}'
            print(f"[Playwright] {self.last_playwright_error}")
            return None
    
    def download_video_aria2c(self, download_url, filename):
        """使用 aria2c 下载视频文件"""
        if download_url.startswith('//'):
            download_url = 'https:' + download_url
            
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)
            
        print(f"[下载URL] {download_url}")
        print(f"[保存路径] {filename}")
        
        # 构建 aria2c 命令
        cmd = [
            'aria2c',
            download_url,
            '-o', filename,
            '-x', '16',
            '-s', '16',
            '-c',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--header=Accept: video/mp4,video/*;q=0.9,*/*;q=0.8',
            '--header=Referer: https://www.iwara.tv/',
            '--check-certificate=false',
            '--timeout=20',
            '--connect-timeout=10',
            '--max-tries=1',
            '--lowest-speed-limit=1K',
            '--summary-interval=5',
            '--console-log-level=warn'
        ]
        
        print(f"[执行命令] aria2c (尝试下载)")
        
        try:
            result = subprocess.run(cmd, timeout=60)
            
            if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"[完成] {os.path.basename(filename)}")
                return True
            else:
                print(f"[失败] aria2c 无法下载，切换到 curl")
                
        except subprocess.TimeoutExpired:
            print(f"[超时] aria2c 超时，切换到 curl")
            try:
                subprocess.run(['pkill', '-f', f'aria2c.*{os.path.basename(filename)}'], capture_output=True)
            except:
                pass
                
        except Exception as e:
            print(f"[错误] aria2c 失败: {e}")
            
        # 清理残留文件
        if os.path.exists(filename + '.aria2'):
            os.remove(filename + '.aria2')
        if os.path.exists(filename) and os.path.getsize(filename) == 0:
            os.remove(filename)
            
        return self.download_video_curl(download_url, filename)
        
    def download_video_curl(self, download_url, filename):
        """使用 curl 下载"""
        print(f"[curl] 开始下载 {os.path.basename(filename)}")
        
        cmd = [
            'curl',
            '-L',
            '-o', filename,
            '-C', '-',
            '--connect-timeout', '30',
            '--max-time', '600',
            '--retry', '1',
            '--retry-delay', '5',
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '-H', 'Accept: video/mp4,video/*;q=0.9,*/*;q=0.8',
            '-H', 'Referer: https://www.iwara.tv/',
            '--compressed',
            '--insecure',
            download_url
        ]
        
        try:
            print("[curl] 下载中...")
            result = subprocess.run(cmd)
            
            if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"[完成] {os.path.basename(filename)} ✓")
                return True
            else:
                print(f"[错误] curl 下载失败，返回码: {result.returncode}")
                return self.download_video_wget(download_url, filename)
                
        except FileNotFoundError:
            print("[错误] curl 未安装，尝试 wget")
            return self.download_video_wget(download_url, filename)
        except Exception as e:
            print(f"[错误] curl 失败: {e}")
            return self.download_video_wget(download_url, filename)
            
    def download_video_wget(self, download_url, filename):
        """使用 wget 作为最终备选"""
        print(f"[wget] 最终尝试下载")
        
        cmd = [
            'wget',
            '-O', filename,
            '-c',
            '--timeout=10',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--header=Accept: video/mp4,video/*;q=0.9,*/*;q=0.8',
            '--header=Referer: https://www.iwara.tv/',
            '--no-check-certificate',
            download_url
        ]
        
        try:
            result = subprocess.run(cmd)
            
            if result.returncode == 0 and os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"[完成] {os.path.basename(filename)} (wget) ✓")
                return True
            else:
                print(f"[错误] 所有下载方式都失败了")
                return False
                
        except Exception as e:
            print(f"[错误] wget 失败: {e}")
            return False
            
    def process_video(self, video_id, json_filename, save_dir='downloads'):
        """处理单个视频 - 使用 Playwright 获取视频信息"""
        # 重置错误信息
        self.last_playwright_error = None
        
        # 使用 Playwright 获取视频信息
        video_data = self.get_video_info_playwright(video_id)
        
        if not video_data:
            error_reason = self.last_playwright_error or 'Playwright 获取视频信息失败（未知原因）'
            self.failed_downloads.append({
                'id': video_id,
                'json_file': json_filename,
                'reason': error_reason,
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            print(f"[错误] {error_reason}")
            return False
            
        # 获取最佳质量的视频
        best_video = video_data.get('best_video')
        if not best_video:
            self.failed_downloads.append({
                'id': video_id,
                'json_file': json_filename,
                'reason': '无可用视频质量',
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return False
            
        print(f"[选择质量] {best_video['name']}")
        
        # 获取下载URL
        download_url = best_video.get('download_url')
        if not download_url:
            self.failed_downloads.append({
                'id': video_id,
                'json_file': json_filename,
                'reason': '视频无下载链接',
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return False
            
        # 使用与JSON文件相同的文件名（去掉.json后缀，加上.mp4）
        base_name = os.path.splitext(os.path.basename(json_filename))[0]
        filename = os.path.join(save_dir, f"{base_name}.mp4")
        
        # 下载视频
        success = self.download_video_aria2c(download_url, filename)
        
        if not success:
            self.failed_downloads.append({
                'id': video_id,
                'json_file': json_filename,
                'reason': '下载失败（网络或文件问题）',
                'download_url': download_url,
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        return success
        
    def process_json_file(self, json_path, save_dir='downloads'):
        """处理单个 JSON 文件"""
        try:
            # 先检查对应的MP4文件是否已存在
            base_name = os.path.splitext(os.path.basename(json_path))[0]
            mp4_filename = os.path.join(save_dir, f"{base_name}.mp4")
            
            if os.path.exists(mp4_filename) and os.path.getsize(mp4_filename) > 0:
                print(f"[跳过] 文件已存在: {base_name}.mp4")
                self.skip_count += 1
                return True  # 返回True表示"成功"（已存在）
            
            # 读取JSON文件
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            video_id = data.get('id')
            if not video_id:
                print(f"[警告] JSON 文件无 ID: {json_path}")
                self.failed_downloads.append({
                    'json_file': json_path,
                    'reason': 'JSON文件中无视频ID',
                    'time': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                return False
                
            print(f"\n[处理] {os.path.basename(json_path)}")
            
            return self.process_video(video_id, json_path, save_dir)
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON解析错误: {e}"
            print(f"[错误] {error_msg} - {json_path}")
            self.failed_downloads.append({
                'json_file': json_path,
                'reason': error_msg,
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return False
        except Exception as e:
            error_msg = f"读取文件错误: {str(e)}"
            print(f"[错误] {error_msg} - {json_path}")
            self.failed_downloads.append({
                'json_file': json_path,
                'reason': error_msg,
                'time': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            return False
            
    def process_directory(self, directory_path, save_dir='downloads'):
        """处理整个目录的 JSON 文件"""
        json_files = glob.glob(os.path.join(directory_path, '*.json'))
        total = len(json_files)
        
        if total == 0:
            print(f"[警告] 目录中没有 JSON 文件: {directory_path}")
            return
            
        print(f"[信息] 找到 {total} 个 JSON 文件")
        print(f"[信息] 源目录: {directory_path}")
        
        # 自动创建保存目录
        os.makedirs(save_dir, exist_ok=True)
        abs_save_dir = os.path.abspath(save_dir)
        print(f"[信息] 保存目录: {abs_save_dir}")
        
        # 清理未完成的下载
        print("\n[清理] 检查未完成的下载...")
        aria2_files = glob.glob(os.path.join(save_dir, '*.aria2'))
        if aria2_files:
            print(f"[清理] 发现 {len(aria2_files)} 个未完成的下载")
            for aria2_file in aria2_files:
                os.remove(aria2_file)
                print(f"[清理] 删除: {os.path.basename(aria2_file)}")
                
                video_file = aria2_file.replace('.aria2', '')
                if os.path.exists(video_file):
                    os.remove(video_file)
                    print(f"[清理] 删除: {os.path.basename(video_file)}")
        else:
            print("[清理] 没有发现未完成的下载")
        
        # 重置计数器
        self.skip_count = 0
        success_count = 0
        
        for i, json_file in enumerate(json_files, 1):
            print(f"\n========== 进度: {i}/{total} ==========")
            result = self.process_json_file(json_file, save_dir)
            if result:
                success_count += 1
            
        # 计算真正下载的数量
        download_count = success_count - self.skip_count
        
        # 输出统计
        print(f"\n========== 完成 ==========")
        print(f"总计: {total} 个文件")
        print(f"成功: {success_count} 个")
        print(f"  - 已存在(跳过): {self.skip_count} 个")
        print(f"  - 新下载: {download_count} 个")
        print(f"失败: {total - success_count} 个")
        print(f"视频保存在: {abs_save_dir}")
        
        # 保存失败记录
        if self.failed_downloads:
            failed_file = os.path.join(save_dir, 'failed_downloads.json')
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_downloads, f, ensure_ascii=False, indent=2)
            print(f"\n失败记录已保存到: {failed_file}")
            
            # 打印失败摘要
            print("\n失败摘要:")
            error_counts = {}
            for fail in self.failed_downloads:
                reason = fail.get('reason', '未知原因')
                error_counts[reason] = error_counts.get(reason, 0) + 1
            
            for reason, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {reason}: {count} 个")

def main():
    # 创建下载器（不需要 bearer_token，因为使用 Playwright）
    downloader = IwaraBatchDownloader()
    
    # 默认下载目录
    save_dir = 'downloads'
    
    # 处理选项
    if len(sys.argv) > 1:
        path = sys.argv[1]
        
        # 如果有第二个参数，作为保存目录
        if len(sys.argv) > 2:
            save_dir = sys.argv[2]
            
        if os.path.isfile(path) and path.endswith('.json'):
            # 处理单个文件
            downloader.process_json_file(path, save_dir)
        elif os.path.isdir(path):
            # 处理整个目录
            downloader.process_directory(path, save_dir)
        else:
            print(f"[错误] 无效路径: {path}")
    else:
        # 默认处理当前目录下的 2025-06 文件夹
        default_dir = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/classification/2025-06"
        if os.path.exists(default_dir):
            downloader.process_directory(default_dir, save_dir)
        else:
            print("用法:")
            print("  python script.py <json文件或目录路径> [保存目录]")
            print("")
            print("示例:")
            print("  python script.py ./video.json")
            print("  python script.py ./video.json /path/to/save")
            print("  python script.py /path/to/json/directory")
            print("  python script.py /path/to/json/directory /path/to/save")

if __name__ == "__main__":
    main()                                                                                                                                                                                                                                                                               ./see_json.py                                                                                       0000644 0000000 0000000 00000002470 15023011603 012062  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
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
    main()                                                                                                                                                                                                        ./separate_videos.py                                                                                0000644 0000000 0000000 00000040427 15023454160 013447  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                   #!/usr/bin/env python3
"""
批量分离视频数据 - 修正版本
正确分类embedUrl视频和正常视频
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback

def format_size(bytes):
    """格式化文件大小"""
    if bytes is None:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"

def is_embed_video(video):
    """
    判断是否为外链视频
    外链视频定义：embedUrl 字段有实际的URL值（不是null，不是空字符串）
    """
    embed_url = video.get("embedUrl")
    # 只有当 embedUrl 是一个非空字符串时，才是外链视频
    return isinstance(embed_url, str) and len(embed_url.strip()) > 0

def is_normal_video(video):
    """
    判断是否为正常视频
    正常视频定义：
    1. embedUrl 为 null 或空
    2. file 对象存在
    3. file.size > 0
    """
    # 检查 embedUrl
    if is_embed_video(video):
        return False
    
    # 检查 file 对象
    file_info = video.get("file")
    if not isinstance(file_info, dict):
        return False
    
    # 检查 file size
    file_size = file_info.get("size", 0)
    if not isinstance(file_size, (int, float)) or file_size <= 0:
        return False
    
    return True

def classify_video(video):
    """
    对单个视频进行详细分类
    返回: (类型, 问题描述列表)
    """
    problems = []
    
    # 检查 embedUrl
    embed_url = video.get("embedUrl")
    if isinstance(embed_url, str) and len(embed_url.strip()) > 0:
        problems.append(f"embed_url({embed_url[:50]}...)")
    
    # 检查 file
    file_info = video.get("file")
    if file_info is None:
        problems.append("no_file")
    elif not isinstance(file_info, dict):
        problems.append(f"invalid_file_type({type(file_info).__name__})")
    else:
        # 检查 file size
        file_size = file_info.get("size")
        if file_size is None:
            problems.append("no_file_size")
        elif not isinstance(file_size, (int, float)):
            problems.append(f"invalid_size_type({type(file_size).__name__})")
        elif file_size <= 0:
            problems.append(f"zero_size({file_size})")
    
    # 确定类型
    if not problems:
        return "normal", []
    else:
        return "problem", problems

def separate_videos(videos):
    """
    分离视频列表
    返回: (正常视频列表, 问题视频列表, 统计信息)
    """
    normal_videos = []
    problem_videos = []
    
    # 详细统计
    stats = {
        "total": len(videos),
        "normal": 0,
        "embed_url": 0,
        "no_file": 0,
        "zero_size": 0,
        "other_problems": 0,
        "problem_details": {}
    }
    
    for i, video in enumerate(videos):
        try:
            video_type, problems = classify_video(video)
            
            if video_type == "normal":
                normal_videos.append(video)
                stats["normal"] += 1
            else:
                # 添加调试信息
                video["_debug_info"] = {
                    "index": i,
                    "problems": problems,
                    "embedUrl_value": video.get("embedUrl"),
                    "embedUrl_type": type(video.get("embedUrl")).__name__,
                    "has_file": "file" in video,
                    "file_type": type(video.get("file")).__name__ if "file" in video else "N/A"
                }
                
                if "file" in video and isinstance(video.get("file"), dict):
                    video["_debug_info"]["file_size"] = video["file"].get("size")
                
                problem_videos.append(video)
                
                # 更新统计
                for problem in problems:
                    if problem.startswith("embed_url"):
                        stats["embed_url"] += 1
                    elif problem == "no_file":
                        stats["no_file"] += 1
                    elif problem.startswith("zero_size"):
                        stats["zero_size"] += 1
                    else:
                        stats["other_problems"] += 1
                    
                    # 记录详细问题
                    if problem not in stats["problem_details"]:
                        stats["problem_details"][problem] = 0
                    stats["problem_details"][problem] += 1
                    
        except Exception as e:
            print(f"  ⚠️  处理视频 {i} 时出错: {e}")
            # 出错的视频归入问题视频
            video["_error"] = str(e)
            problem_videos.append(video)
    
    return normal_videos, problem_videos, stats

def validate_separation(normal_videos, problem_videos):
    """验证分类结果"""
    print("\n📋 验证分类结果...")
    
    # 检查正常视频
    errors = []
    for i, video in enumerate(normal_videos[:5]):  # 抽查前5个
        if is_embed_video(video):
            errors.append(f"正常视频 {i} 有embedUrl: {video.get('embedUrl')}")
        if not video.get("file") or video.get("file", {}).get("size", 0) <= 0:
            errors.append(f"正常视频 {i} 文件信息异常")
    
    # 检查问题视频
    for i, video in enumerate(problem_videos[:5]):  # 抽查前5个
        if not is_embed_video(video) and is_normal_video(video):
            errors.append(f"问题视频 {i} 应该是正常视频")
    
    if errors:
        print("  ❌ 发现分类错误:")
        for error in errors:
            print(f"     - {error}")
    else:
        print("  ✅ 抽查通过")

def process_chunk_file(input_path, normal_output_path, problem_output_path):
    """处理单个chunk文件"""
    print(f"\n处理文件: {input_path.name}")
    
    try:
        # 读取数据
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or "videos" not in data:
            print(f"  ⚠️  文件格式不正确，跳过")
            return None
        
        # 分离视频
        original_videos = data["videos"]
        normal_videos, problem_videos, stats = separate_videos(original_videos)
        
        # 验证分类
        validate_separation(normal_videos, problem_videos)
        
        # 保存正常视频
        normal_data = data.copy()
        normal_data["videos"] = normal_videos
        normal_data["_metadata"] = {
            "processed_at": datetime.now().isoformat(),
            "original_count": stats["total"],
            "retained_count": stats["normal"],
            "type": "normal_videos",
            "classification_criteria": {
                "embedUrl": "must be null or empty",
                "file": "must exist and be dict",
                "file.size": "must be > 0"
            }
        }
        
        normal_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(normal_output_path, 'w', encoding='utf-8') as f:
            json.dump(normal_data, f, ensure_ascii=False, indent=2)
        
        # 保存问题视频
        problem_data = data.copy()
        problem_data["videos"] = problem_videos
        problem_data["_metadata"] = {
            "processed_at": datetime.now().isoformat(),
            "original_count": stats["total"],
            "problem_count": len(problem_videos),
            "type": "problem_videos",
            "problems_summary": stats["problem_details"]
        }
        
        problem_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(problem_output_path, 'w', encoding='utf-8') as f:
            json.dump(problem_data, f, ensure_ascii=False, indent=2)
        
        # 显示统计
        print(f"  ✅ 处理完成:")
        print(f"     总视频数: {stats['total']}")
        print(f"     正常视频: {stats['normal']} ({stats['normal']/stats['total']*100:.1f}%)")
        print(f"     问题视频: {len(problem_videos)} ({len(problem_videos)/stats['total']*100:.1f}%)")
        
        if stats["problem_details"]:
            print(f"     问题详情:")
            for problem, count in sorted(stats["problem_details"].items()):
                print(f"       - {problem}: {count}")
        
        # 显示一些示例
        if normal_videos:
            print(f"\n     正常视频示例:")
            video = normal_videos[0]
            print(f"       ID: {video.get('id')}")
            print(f"       embedUrl: {video.get('embedUrl')}")
            print(f"       file.size: {format_size(video.get('file', {}).get('size'))}")
        
        if problem_videos:
            print(f"\n     问题视频示例:")
            video = problem_videos[0]
            print(f"       ID: {video.get('id')}")
            print(f"       embedUrl: {video.get('embedUrl')}")
            if '_debug_info' in video:
                print(f"       问题: {', '.join(video['_debug_info']['problems'])}")
        
        return stats
        
    except Exception as e:
        print(f"  ❌ 处理失败: {e}")
        traceback.print_exc()
        return None

def process_all_chunks(input_dir, normal_output_dir, problem_output_dir):
    """处理所有chunk文件"""
    input_path = Path(input_dir)
    normal_output_path = Path(normal_output_dir)
    problem_output_path = Path(problem_output_dir)
    
    if not input_path.exists():
        print(f"错误：输入目录不存在 - {input_dir}")
        return
    
    # 创建输出目录
    normal_output_path.mkdir(parents=True, exist_ok=True)
    problem_output_path.mkdir(parents=True, exist_ok=True)
    
    # 找到所有chunk文件
    chunk_files = sorted(input_path.glob("chunk_*.json"))
    
    if not chunk_files:
        print(f"错误：在 {input_dir} 中没有找到chunk文件")
        return
    
    print(f"找到 {len(chunk_files)} 个chunk文件")
    print("=" * 80)
    
    # 总体统计
    total_stats = {
        "files_processed": 0,
        "files_failed": 0,
        "total_videos": 0,
        "total_normal": 0,
        "total_embed_url": 0,
        "total_no_file": 0,
        "total_zero_size": 0,
        "all_problem_details": {}
    }
    
    # 处理每个文件
    for chunk_file in chunk_files:
        normal_output_file = normal_output_path / chunk_file.name
        problem_output_file = problem_output_path / chunk_file.name
        
        stats = process_chunk_file(chunk_file, normal_output_file, problem_output_file)
        
        if stats:
            total_stats["files_processed"] += 1
            total_stats["total_videos"] += stats["total"]
            total_stats["total_normal"] += stats["normal"]
            total_stats["total_embed_url"] += stats["embed_url"]
            total_stats["total_no_file"] += stats["no_file"]
            total_stats["total_zero_size"] += stats["zero_size"]
            
            # 合并问题详情
            for problem, count in stats["problem_details"].items():
                if problem not in total_stats["all_problem_details"]:
                    total_stats["all_problem_details"][problem] = 0
                total_stats["all_problem_details"][problem] += count
        else:
            total_stats["files_failed"] += 1
    
    # 复制其他文件
    print("\n复制其他文件...")
    for file in input_path.glob("*.json"):
        if not file.name.startswith("chunk_"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 保存到两个目录
                for output_path in [normal_output_path, problem_output_path]:
                    output_file = output_path / file.name
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"  ✅ 复制: {file.name}")
            except Exception as e:
                print(f"  ❌ 复制失败 {file.name}: {e}")
    
    # 显示总体统计
    print("\n" + "=" * 80)
    print("📊 总体统计:")
    print(f"  处理文件数: {total_stats['files_processed']}/{len(chunk_files)}")
    if total_stats["files_failed"] > 0:
        print(f"  失败文件数: {total_stats['files_failed']}")
    
    print(f"\n  视频分类结果:")
    print(f"    总视频数: {total_stats['total_videos']:,}")
    print(f"    ✅ 正常视频: {total_stats['total_normal']:,} "
          f"({total_stats['total_normal']/total_stats['total_videos']*100:.1f}%)")
    
    total_problems = total_stats["total_videos"] - total_stats["total_normal"]
    print(f"    ❌ 问题视频: {total_problems:,} "
          f"({total_problems/total_stats['total_videos']*100:.1f}%)")
    
    print(f"\n  问题类型分布:")
    print(f"    - 外链视频(embedUrl有值): {total_stats['total_embed_url']:,}")
    print(f"    - 无文件信息: {total_stats['total_no_file']:,}")
    print(f"    - 文件大小为0: {total_stats['total_zero_size']:,}")
    
    if total_stats["all_problem_details"]:
        print(f"\n  所有问题详情:")
        for problem, count in sorted(total_stats["all_problem_details"].items(), 
                                   key=lambda x: x[1], reverse=True):
            print(f"    - {problem}: {count:,}")
    
    # 保存处理报告
    report = {
        "processing_time": datetime.now().isoformat(),
        "script_version": "2.0-fixed",
        "classification_rules": {
            "normal_video": {
                "embedUrl": "null or empty string",
                "file": "exists and is dict",
                "file.size": "> 0"
            },
            "problem_video": {
                "embedUrl": "has URL value",
                "OR_file": "null or not dict",
                "OR_file.size": "<= 0"
            }
        },
        "directories": {
            "input": str(input_path),
            "normal_output": str(normal_output_path),
            "problem_output": str(problem_output_path)
        },
        "statistics": total_stats
    }
    
    # 保存报告
    for output_path, dir_type in [(normal_output_path, "normal"), (problem_output_path, "problem")]:
        report_path = output_path / f"classification_report_{dir_type}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 处理完成！")
    print(f"   正常视频保存在: {normal_output_path}")
    print(f"   问题视频保存在: {problem_output_path}")
    print(f"   分类报告已生成")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("批量分离视频数据 - 修正版本")
        print("\n用法:")
        print("  python separate_videos.py [输入目录] [正常视频目录] [问题视频目录]")
        print("\n分类规则:")
        print("  正常视频:")
        print("    - embedUrl 为 null 或空字符串")
        print("    - file 字段存在且是字典")
        print("    - file.size > 0")
        print("  问题视频:")
        print("    - embedUrl 有实际URL值（外链视频）")
        print("    - 或 file 字段为 null")
        print("    - 或 file.size <= 0")
        return
    
    # 默认路径
    input_dir = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/iwara_data"
    normal_output_dir = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/iwara_data_pured"
    problem_output_dir = "/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd/iwara_data_embed"
    
    # 解析参数
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        normal_output_dir = sys.argv[2]
    if len(sys.argv) > 3:
        problem_output_dir = sys.argv[3]
    
    # 确认操作
    print("批量分离视频数据 - 修正版本 v2.0")
    print(f"\n配置:")
    print(f"  输入目录: {input_dir}")
    print(f"  正常视频输出: {normal_output_dir}")
    print(f"  问题视频输出: {problem_output_dir}")
    
    print("\n分类标准:")
    print("  ✅ 正常视频:")
    print("     - embedUrl = null 或 空字符串")
    print("     - file 对象存在")
    print("     - file.size > 0")
    print("  ❌ 问题视频:")
    print("     - embedUrl 有URL值（外链）")
    print("     - 或 file 不存在")
    print("     - 或 file.size <= 0")
    
    # 执行处理
    process_all_chunks(input_dir, normal_output_dir, problem_output_dir)

if __name__ == "__main__":
    main()                                                                                                                                                                                                                                         ./untitled.py                                                                                       0000644 0000000 0000000 00000000000 15023454136 012104  0                                                                                                    ustar   root                            root                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   