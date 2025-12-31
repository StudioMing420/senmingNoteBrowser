#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建简单的图标文件
"""

from PIL import Image, ImageDraw
import os

# 创建icons文件夹
if not os.path.exists("icons"):
    os.makedirs("icons")

# 图标尺寸
size = (64, 64)

# 定义图标颜色
colors = {
    "folder": (52, 152, 219),
    "txt": (46, 204, 113),
    "md": (155, 89, 182),
    "html": (230, 126, 34),
    "doc": (41, 128, 185),
    "pdf": (231, 76, 60),
    "video": (192, 57, 43),
    "audio": (142, 68, 173)
}

# 创建图标
for icon_name, color in colors.items():
    # 创建图像
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

    # 添加文字
    if icon_name == "folder":
        text = "📁"
    elif icon_name == "txt":
        text = "TXT"
    elif icon_name == "md":
        text = "MD"
    elif icon_name == "html":
        text = "HTML"
    elif icon_name == "doc":
        text = "DOC"
    elif icon_name == "pdf":
        text = "PDF"
    elif icon_name == "video":
        text = "🎬"
    elif icon_name == "audio":
        text = "🎵"
    else:
        text = icon_name.upper()

    # 保存图像
    img.save(f"icons/{icon_name}.png")
    print(f"创建图标: icons/{icon_name}.png")

print("所有图标已创建完成！")