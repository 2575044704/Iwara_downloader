#!/usr/bin/env python3
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
    main()