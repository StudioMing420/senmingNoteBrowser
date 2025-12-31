#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包脚本 - 将森明笔记打包成可执行文件
修复版：解决--add-data参数格式问题
"""

import os
import sys
import shutil
import platform
from pathlib import Path
import PyInstaller.__main__


def get_os_separator():
    """获取操作系统特定的路径分隔符"""
    if platform.system() == "Windows":
        return ';'  # Windows使用分号
    else:
        return ':'  # Linux/Mac使用冒号


def create_icons_folder():
    """创建必要的图标文件（如果不存在）"""
    icons_dir = Path("icons")
    icons_dir.mkdir(exist_ok=True)

    # 创建基本图标（如果不存在）
    icon_files = {
        "folder.png": "文件夹图标",
        "txt.png": "文本文件图标",
        "md.png": "Markdown图标",
        "html.png": "HTML图标",
        "doc.png": "Word文档图标",
        "pdf.png": "PDF图标",
        "video.png": "视频文件图标",
        "audio.png": "音频文件图标"
    }

    for icon_file, description in icon_files.items():
        if not (icons_dir / icon_file).exists():
            print(f"警告: {icon_file} 不存在，请将{description}放入icons文件夹")

    return icons_dir


def create_logo():
    """检查logo文件"""
    logo_path = Path("logo.ico")
    if not logo_path.exists():
        print("警告: logo.ico 不存在，请创建256x256像素的图标文件并命名为logo.ico")
        print("可以使用在线工具将图片转换为ico格式")
        return False
    return True


def clean_build_folders():
    """清理之前的构建文件"""
    build_dirs = ["build", "dist"]
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"已清理: {dir_name}")
            except Exception as e:
                print(f"清理 {dir_name} 失败: {e}")


def create_simple_icons():
    """创建简单的默认图标（如果icons文件夹为空）"""
    icons_dir = Path("icons")

    # 检查icons文件夹是否为空
    if icons_dir.exists() and any(icons_dir.iterdir()):
        return True  # 已经有图标文件

    print("icons文件夹为空，创建简单的默认图标...")

    try:
        from PIL import Image, ImageDraw
        print("安装Pillow库以创建默认图标...")

        # 尝试导入PIL，如果不存在则跳过
        colors = {
            "folder.png": (52, 152, 219),
            "txt.png": (46, 204, 113),
            "md.png": (155, 89, 182),
            "html.png": (230, 126, 34),
            "doc.png": (41, 128, 185),
            "pdf.png": (231, 76, 60),
            "video.png": (192, 57, 43),
            "audio.png": (142, 68, 173)
        }

        size = (64, 64)

        for icon_name, color in colors.items():
            img = Image.new('RGBA', size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # 绘制圆角矩形背景
            padding = 8
            draw.rounded_rectangle(
                [padding, padding, size[0] - padding, size[1] - padding],
                radius=10,
                fill=color,
                outline=(255, 255, 255),
                width=2
            )

            img.save(str(icons_dir / icon_name))
            print(f"创建图标: {icon_name}")

        print("所有默认图标已创建完成！")
        return True

    except ImportError:
        print("未安装Pillow库，无法创建默认图标。请手动添加图标文件到icons文件夹。")
        return False
    except Exception as e:
        print(f"创建图标时出错: {e}")
        return False


def main():
    print("开始打包森明笔记...")
    print("=" * 50)

    # 获取操作系统特定的分隔符
    separator = get_os_separator()
    print(f"检测到操作系统: {platform.system()}, 使用分隔符: '{separator}'")

    # 检查必要文件
    create_icons_folder()

    # 如果icons文件夹为空，创建简单图标
    if not create_simple_icons():
        print("提示: 请手动创建图标文件或安装Pillow库")
        print("安装Pillow: pip install Pillow")

    if not create_logo():
        print("提示: 可以在打包完成后手动添加logo.ico到dist文件夹")

    # 清理之前的构建
    clean_build_folders()

    # 打包配置
    main_script = "main.py"
    app_name = "森明笔记"

    # PyInstaller参数 - 使用列表构建，避免格式问题
    pyinstaller_args = [
        main_script,
        '--name=' + app_name,
        '--windowed',  # 不显示控制台窗口
        '--clean',  # 清理临时文件
        '--onefile',  # 打包成单个exe
    ]

    # 添加图标（如果有）
    if os.path.exists("logo.ico"):
        pyinstaller_args.append('--icon=logo.ico')

    # 添加数据文件 - 正确格式
    pyinstaller_args.extend([
        '--add-data', f'icons{separator}icons',
    ])

    # 如果logo.ico存在，也添加到数据文件
    if os.path.exists("logo.ico"):
        pyinstaller_args.extend([
            '--add-data', f'logo.ico{separator}.',
        ])

    # 添加隐藏导入
    hidden_imports = [
        'PyQt5',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.sip',
    ]

    for imp in hidden_imports:
        pyinstaller_args.extend(['--hidden-import', imp])

    # 添加其他选项
    pyinstaller_args.extend([
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'numpy',
        '--exclude-module', 'pandas',
        '--exclude-module', 'scipy',
    ])

    print(f"打包命令: pyinstaller {' '.join(pyinstaller_args)}")
    print("=" * 50)
    print("开始打包，这可能需要几分钟...")

    try:
        # 运行PyInstaller
        print("正在运行PyInstaller...")
        PyInstaller.__main__.run(pyinstaller_args)

        print("=" * 50)
        print("打包完成！")

        # 检查生成的可执行文件
        exe_path = os.path.join("dist", app_name + (".exe" if platform.system() == "Windows" else ""))
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # 转换为MB
            print(f"可执行文件位置: {exe_path}")
            print(f"文件大小: {file_size:.2f} MB")
        else:
            print(f"警告: 未找到可执行文件 {exe_path}")
            print("检查dist文件夹中的文件:")
            dist_dir = Path("dist")
            if dist_dir.exists():
                for file in dist_dir.iterdir():
                    print(f"  - {file.name}")

        print("\n重要提示:")
        print("1. 将可执行文件复制到任何电脑都可以运行")
        print("2. 首次运行会在程序所在目录创建config.json配置文件")
        print("3. 如果缺少图标，请确保icons文件夹与exe文件在同一目录")
        print("4. 可以在设置中修改笔记文件夹路径")

    except Exception as e:
        print(f"打包失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()