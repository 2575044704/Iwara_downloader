#!/usr/bin/env python3
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
    main()