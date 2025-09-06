#!/usr/bin/env python3
"""
自动安装 Playwright 并进行百度测试
支持在 VNC 中显示执行过程
"""

import subprocess
import sys
import os

# 设置 DISPLAY 环境变量以在 VNC 中显示
os.environ['DISPLAY'] = ':1'
print(f"[环境] DISPLAY 已设置为: {os.environ['DISPLAY']}")

def install_package(package_name):
    """使用 pip 安装包"""
    print(f"[安装] 正在安装 {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"[成功] {package_name} 安装完成")
        return True
    except subprocess.CalledProcessError:
        print(f"[失败] {package_name} 安装失败")
        return False

def check_and_install_playwright():
    """检查并安装 Playwright"""
    try:
        import playwright
        print("[检查] Playwright 已安装")
        return True
    except ImportError:
        print("[检查] Playwright 未安装，开始安装...")
        if install_package("playwright"):
            # 重新导入以确保安装成功
            try:
                import playwright
                return True
            except ImportError:
                return False
        return False

def install_browsers():
    """安装 Playwright 浏览器"""
    print("[浏览器] 开始安装 Chromium 浏览器...")
    try:
        # 安装 Chromium
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[成功] Chromium 浏览器安装完成")
            
            # 尝试安装系统依赖（在某些环境中可能需要）
            print("[依赖] 尝试安装系统依赖...")
            deps_result = subprocess.run(
                [sys.executable, "-m", "playwright", "install-deps", "chromium"],
                capture_output=True,
                text=True
            )
            if deps_result.returncode != 0:
                print("[提示] 系统依赖安装失败，但可能不影响使用")
                
            return True
        else:
            print(f"[错误] 浏览器安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"[错误] 安装浏览器时出错: {e}")
        return False

def simple_baidu_test():
    """简单的百度测试 - 支持 VNC 显示"""
    print("\n" + "="*50)
    print("开始百度测试 (VNC 模式)")
    print("="*50)
    print(f"[显示] 使用 DISPLAY: {os.environ.get('DISPLAY', '未设置')}")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            print("[启动] 正在启动浏览器（有界面模式）...")
            
            # 使用有头模式，在 VNC 中显示
            browser = p.chromium.launch(
                headless=False,  # 改为 False 以在 VNC 中显示
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    # 移除 '--single-process' 因为在有头模式下可能会有问题
                    '--disable-gpu-sandbox',
                    '--window-size=1280,720',  # 设置窗口大小
                    '--window-position=100,100',  # 设置窗口位置
                    '--force-device-scale-factor=1'  # 强制缩放因子
                ]
            )
            
            print("[浏览] 创建新页面...")
            page = browser.new_page()
            
            # 设置视口大小
            page.set_viewport_size({"width": 1280, "height": 720})
            
            print("[导航] 访问百度...")
            print("[提示] 请在 VNC 查看器中观察浏览器窗口")
            page.goto('https://www.baidu.com', wait_until='domcontentloaded', timeout=30000)
            
            # 等待一下让用户看到页面
            page.wait_for_timeout(2000)
            
            # 获取页面标题
            title = page.title()
            print(f"[成功] 页面标题: {title}")
            
            # 截图
            screenshot_path = "baidu_test.png"
            page.screenshot(path=screenshot_path)
            print(f"[截图] 已保存到: {screenshot_path}")
            
            # 获取当前目录的绝对路径
            abs_path = os.path.abspath(screenshot_path)
            print(f"[路径] 完整路径: {abs_path}")
            
            # 检查搜索框是否存在
            search_box = page.query_selector('#kw')
            if search_box:
                print("[成功] 找到百度搜索框")
                
                # 缓慢输入测试文本，让用户能看到输入过程
                print("[输入] 正在输入搜索文本...")
                page.type('#kw', 'Playwright 测试成功', delay=100)  # 每个字符间隔100ms
                page.wait_for_timeout(2000)
                
                # 点击搜索按钮
                print("[点击] 点击搜索按钮...")
                page.click('#su')
                page.wait_for_timeout(3000)  # 等待搜索结果
                
                # 再次截图
                screenshot_with_results = "baidu_test_results.png"
                page.screenshot(path=screenshot_with_results)
                print(f"[截图] 搜索结果截图: {screenshot_with_results}")
                
                # 滚动页面
                print("[滚动] 向下滚动页面...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                page.wait_for_timeout(2000)
            
            # 保持浏览器打开一段时间，让用户观察
            print("\n[等待] 浏览器将保持打开 5 秒...")
            page.wait_for_timeout(5000)
            
            browser.close()
            print("[关闭] 浏览器已关闭")
            
            print("\n[✓] 测试完全成功！")
            return True
            
    except Exception as e:
        print(f"\n[✗] 测试失败: {e}")
        print("\n[调试信息]")
        print(f"Python 版本: {sys.version}")
        print(f"当前目录: {os.getcwd()}")
        print(f"DISPLAY: {os.environ.get('DISPLAY', '未设置')}")
        print(f"环境: {os.environ.get('MODAL_ENVIRONMENT', 'Unknown')}")
        
        # VNC 相关的额外调试
        print("\n[VNC 检查]")
        # 检查 X11 是否可用
        try:
            result = subprocess.run(['xdpyinfo'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                print("✓ X11 服务器正在运行")
            else:
                print("✗ X11 服务器可能未运行")
        except:
            print("✗ 无法执行 xdpyinfo 命令")
            
        return False

def main():
    """主函数"""
    print("Playwright 自动安装和测试脚本 (VNC 版本)")
    print("="*50)
    
    # 检查 DISPLAY 环境变量
    if not os.environ.get('DISPLAY'):
        print("[警告] DISPLAY 环境变量未设置，正在设置为 :1")
        os.environ['DISPLAY'] = ':1'
    
    print(f"[环境] 当前 DISPLAY: {os.environ['DISPLAY']}")
    
    # 步骤 1: 安装 Playwright
    if not check_and_install_playwright():
        print("\n[错误] 无法安装 Playwright")
        print("请手动运行: pip install playwright")
        sys.exit(1)
    
    # 步骤 2: 安装浏览器
    if not install_browsers():
        print("\n[警告] 浏览器安装可能未完成")
        print("继续尝试运行测试...")
    
    # 步骤 3: 运行测试
    print("\n准备运行测试...")
    print("[重要] 请确保 VNC 服务器正在运行，并已连接 VNC 查看器")
    print("[提示] 浏览器窗口将在 VNC 中显示\n")
    
    success = simple_baidu_test()
    
    if success:
        print("\n" + "="*50)
        print("所有测试通过！Playwright 工作正常")
        print("="*50)
        
        # 显示生成的文件
        files = ["baidu_test.png", "baidu_test_results.png"]
        existing_files = [f for f in files if os.path.exists(f)]
        if existing_files:
            print("\n生成的文件:")
            for f in existing_files:
                size = os.path.getsize(f)
                print(f"  - {f} ({size} bytes)")
    else:
        print("\n测试失败，请检查错误信息")
        
        # 提供 VNC 相关的调试建议
        print("\n可能的解决方案:")
        print("1. 确保 VNC 服务器正在运行")
        print("2. 检查 DISPLAY 环境变量是否正确（应该是 :1）")
        print("3. 确保有 X11 相关的库和依赖")
        print("4. 尝试运行: export DISPLAY=:1")
        print("5. 如果在 Docker 中，确保容器有 X11 访问权限")

if __name__ == "__main__":
    main()
