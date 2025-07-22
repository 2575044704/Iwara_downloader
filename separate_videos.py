#!/usr/bin/env python3
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
    main()