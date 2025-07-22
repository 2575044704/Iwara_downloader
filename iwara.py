#!/usr/bin/env python3
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

