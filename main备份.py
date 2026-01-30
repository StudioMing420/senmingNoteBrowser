#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
森明笔记浏览器 - 打包优化版
作者: msm_bcf_works@163.com
"""

import os
import sys
import json
import time
import traceback
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# PyQt5相关导入
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


# 获取程序运行路径
def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持打包后运行"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# 配置管理类
class Config:
    DEFAULT_CONFIG = {
        "notes_folder": str(Path.home() / "Documents" / "Notes"),
        "file_types": {
            "txt,text": {"icon": "txt.png", "external": "notepad.exe"},
            "md": {"icon": "md.png", "external": ""},
            "html,htm": {"icon": "html.png", "external": ""},
            "doc,docx": {"icon": "doc.png", "external": ""},
            "pdf": {"icon": "pdf.png", "external": ""},
            "mp4,avi,mkv,mov,wmv": {"icon": "video.png", "external": ""},
            "mp3,wav,flac,ogg": {"icon": "audio.png", "external": ""}
        },
        "view_mode": "list",
        "sort_by": "name_asc",
        "theme": "light",
        "window_geometry": None,
        "close_action": "hide_to_tray",  # 新增：关闭按钮行为，可选值："hide_to_tray" 或 "quit"
        "pinned_notes": []  # 新增：置顶笔记列表，存储笔记的绝对路径
    }

    def __init__(self, config_path="config.json"):
        # 优先使用可执行文件所在目录的config.json
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_path = os.path.join(exe_dir, config_path)
        self.config_path = config_path
        self.data = self.load_config()
        if self.data.get("theme") == "default":
            self.data["theme"] = "light"

        # 确保配置文件中的file_types是正确的
        self._validate_file_types()

        # 确保close_action是有效的
        if "close_action" not in self.data:
            self.data["close_action"] = self.DEFAULT_CONFIG["close_action"]

        # 确保pinned_notes存在且是列表
        if "pinned_notes" not in self.data:
            self.data["pinned_notes"] = self.DEFAULT_CONFIG["pinned_notes"].copy()

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, value in self.DEFAULT_CONFIG.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            print(f"加载配置失败: {e}")

        return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def _validate_file_types(self):
        """确保文件类型配置是有效的"""
        if "file_types" not in self.data:
            self.data["file_types"] = self.DEFAULT_CONFIG["file_types"].copy()
        else:
            # 确保没有重复的扩展名
            seen_extensions = set()
            clean_file_types = {}

            for type_str, info in self.data["file_types"].items():
                # 清理扩展名列表
                extensions = [ext.strip().lower() for ext in type_str.split(',')]
                unique_extensions = []

                for ext in extensions:
                    if ext and ext not in seen_extensions:
                        seen_extensions.add(ext)
                        unique_extensions.append(ext)

                if unique_extensions:
                    # 重新构建类型字符串
                    new_type_str = ','.join(unique_extensions)
                    clean_file_types[new_type_str] = info

            self.data["file_types"] = clean_file_types

    def _get_all_extensions(self) -> Set[str]:
        """获取所有支持的文件扩展名"""
        extensions = set()
        for types in self.data["file_types"].keys():
            for ext in [t.strip().lower() for t in types.split(',')]:
                if ext:  # 确保不是空字符串
                    extensions.add(ext.lower())
        return extensions

    def get_file_type_info(self, extension: str) -> Optional[Dict]:
        """获取文件类型信息，如果扩展名不支持则返回None"""
        extension = extension.lower().lstrip('.')
        for types, info in self.data["file_types"].items():
            type_list = [t.strip().lower() for t in types.split(',')]
            if extension in type_list:
                return info.copy()
        return None

    def is_supported_extension(self, extension: str) -> bool:
        """检查扩展名是否受支持"""
        extension = extension.lower().lstrip('.')
        for types in self.data["file_types"].keys():
            type_list = [t.strip().lower() for t in types.split(',')]
            if extension in type_list:
                return True
        return False

    def is_note_pinned(self, note_path: str) -> bool:
        """检查笔记是否已置顶"""
        # 使用绝对路径进行比较
        abs_path = os.path.abspath(note_path)
        return abs_path in self.data["pinned_notes"]

    def pin_note(self, note_path: str) -> bool:
        """置顶笔记"""
        try:
            abs_path = os.path.abspath(note_path)
            if abs_path not in self.data["pinned_notes"]:
                self.data["pinned_notes"].append(abs_path)
                return self.save_config()
            return True
        except Exception as e:
            print(f"置顶笔记失败: {e}")
            return False

    def unpin_note(self, note_path: str) -> bool:
        """取消置顶笔记"""
        try:
            abs_path = os.path.abspath(note_path)
            if abs_path in self.data["pinned_notes"]:
                self.data["pinned_notes"].remove(abs_path)
                return self.save_config()
            return True
        except Exception as e:
            print(f"取消置顶笔记失败: {e}")
            return False


# 文件系统扫描线程
class FileSystemScanner(QThread):
    scan_progress = pyqtSignal(int, int, str)
    scan_complete = pyqtSignal(list)

    def __init__(self, root_path: str, config: Config):
        super().__init__()
        self.root_path = root_path
        self.config = config
        self._is_cancelled = False

    def run(self):
        try:
            notes = self.scan_notes()
            self.scan_complete.emit(notes)
        except Exception as e:
            print(f"扫描错误: {e}")
            traceback.print_exc()
            self.scan_complete.emit([])

    def cancel(self):
        self._is_cancelled = True

    def scan_notes(self) -> List[Dict]:
        notes = []
        if not os.path.exists(self.root_path):
            return notes

        try:
            items = list(os.scandir(self.root_path))
            total = len(items)

            for i, item in enumerate(items):
                if self._is_cancelled:
                    break

                self.scan_progress.emit(i + 1, total, item.name)

                try:
                    if item.is_dir():
                        # 文件夹笔记
                        note_info = self._get_folder_note_info(item)
                        if note_info:
                            notes.append(note_info)
                    elif item.is_file():
                        # 单个文件笔记
                        note_info = self._get_file_note_info(item)
                        if note_info:
                            notes.append(note_info)
                except Exception as e:
                    print(f"处理项目 {item.name} 时出错: {e}")
                    continue

                time.sleep(0.001)

        except Exception as e:
            print(f"扫描目录时出错: {e}")

        return notes

    def _get_folder_note_info(self, item) -> Optional[Dict]:
        """处理文件夹作为笔记的情况"""
        try:
            folder_path = item.path
            folder_name = item.name

            # 在文件夹中查找支持的文件
            main_file = self._find_main_file_in_folder(folder_path)
            if main_file:
                ext = os.path.splitext(main_file)[1].lower().lstrip('.')
                file_type_info = self.config.get_file_type_info(ext)

                # 如果文件类型不支持，跳过这个文件夹
                if not file_type_info:
                    return None

                folder_size = self._calculate_folder_size(folder_path)
                stat = os.stat(main_file)

                return {
                    "name": f"{folder_name}",
                    "original_name": folder_name,
                    "path": main_file,
                    "is_folder": True,
                    "folder_path": folder_path,
                    "total_size": folder_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "type": ext,
                    "icon": file_type_info.get("icon", "folder.png"),
                    "is_pinned": self.config.is_note_pinned(main_file)  # 添加是否置顶标志
                }
            return None
        except Exception as e:
            print(f"获取文件夹笔记信息错误: {e}")
            return None

    def _get_file_note_info(self, item) -> Optional[Dict]:
        """处理单个文件作为笔记的情况"""
        try:
            ext = os.path.splitext(item.name)[1].lower().lstrip('.')

            # 检查是否是支持的文件类型（包括自定义添加的）
            if self.config.is_supported_extension(ext):
                file_type_info = self.config.get_file_type_info(ext)

                # 如果文件类型不支持，跳过这个文件
                if not file_type_info:
                    return None

                stat = item.stat()

                return {
                    "name": item.name,
                    "original_name": item.name,
                    "path": item.path,
                    "is_folder": False,
                    "folder_path": os.path.dirname(item.path),
                    "total_size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "type": ext,
                    "icon": file_type_info.get("icon", "txt.png"),
                    "is_pinned": self.config.is_note_pinned(item.path)  # 添加是否置顶标志
                }
            return None
        except Exception as e:
            print(f"获取文件笔记信息错误: {e}")
            return None

    def _calculate_folder_size(self, folder_path: str) -> int:
        total_size = 0
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        total_size += os.path.getsize(file_path)
                    except:
                        continue
        except:
            pass
        return total_size

    def _find_main_file_in_folder(self, folder_path: str) -> Optional[str]:
        """在文件夹中查找主要文件（支持所有配置的文件类型）"""
        try:
            # 获取所有支持的文件扩展名
            supported_extensions = self.config._get_all_extensions()

            # 查找所有支持的文件
            supported_files = []

            for item in os.scandir(folder_path):
                if item.is_file():
                    filename = item.name
                    ext = os.path.splitext(filename)[1].lower().lstrip('.')

                    # 检查是否是支持的文件类型（包括自定义添加的）
                    if ext in supported_extensions:
                        supported_files.append((item.path, filename, ext))

            # 如果有支持的文件，优先返回特定名称的文件
            if supported_files:
                # 优先返回与文件夹同名的文件
                folder_name = os.path.basename(folder_path)
                for file_path, filename, ext in supported_files:
                    base_name = os.path.splitext(filename)[0]
                    if base_name.lower() == folder_name.lower():
                        return file_path

                # 然后返回默认优先级文件
                priority_names = ["index", "main", "readme", "readme", "main"]
                for name in priority_names:
                    for file_path, filename, ext in supported_files:
                        base_name = os.path.splitext(filename)[0].lower()
                        if base_name == name:
                            return file_path

                # 如果没有特定名称的文件，返回第一个支持的文件
                return supported_files[0][0]

            # 如果没有支持的文件，返回None
            return None

        except Exception as e:
            print(f"查找主文件错误: {e}")
            return None


# 自定义列表项Widget
class CustomListWidgetItem(QWidget):
    def __init__(self, note_info: Dict, theme: str = "light"):
        super().__init__()
        self.note_info = note_info
        self.theme = theme
        self.init_ui()

    def init_ui(self):
        try:
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(8, 8, 8, 8)
            main_layout.setSpacing(10)

            # 图标区域（包含置顶图标）
            icon_widget = QWidget()
            icon_layout = QVBoxLayout()
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_layout.setSpacing(2)

            # 置顶图标（如果笔记已置顶）
            if self.note_info.get("is_pinned", False):
                pin_label = QLabel("📌")
                pin_label.setAlignment(Qt.AlignCenter)
                icon_layout.addWidget(pin_label)

            # 文件图标
            icon_label = QLabel()
            icon_label.setFixedSize(48, 48)

            # 使用相对路径，在打包时会自动包含icons文件夹
            icon_paths = [
                "icons/" + self.note_info.get('icon', 'txt.png'),
                os.path.join(os.path.dirname(__file__), "icons", self.note_info.get('icon', 'txt.png')),
                get_resource_path("icons/" + self.note_info.get('icon', 'txt.png'))
            ]

            pixmap = None
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        pixmap = QPixmap(icon_path)
                        break
                    except:
                        continue

            if pixmap is None or pixmap.isNull():
                pixmap = QPixmap(48, 48)
                pixmap.fill(Qt.lightGray)

            icon_label.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_label.setAlignment(Qt.AlignCenter)
            icon_layout.addWidget(icon_label)
            icon_layout.addStretch()

            icon_widget.setLayout(icon_layout)

            # 时间信息
            time_widget = QWidget()
            time_layout = QVBoxLayout()
            time_layout.setContentsMargins(0, 0, 0, 0)
            time_layout.setSpacing(3)

            created_time = datetime.fromtimestamp(self.note_info["created"]).strftime("%Y-%m-%d %H:%M")
            modified_time = datetime.fromtimestamp(self.note_info["modified"]).strftime("%Y-%m-%d %H:%M")
            size_mb = self.note_info["total_size"] / (1024 * 1024)
            size_label_text = "笔记大小" if self.note_info["is_folder"] else "文件大小"

            created_label = QLabel(f"创建: {created_time}")
            modified_label = QLabel(f"修改: {modified_time}")
            size_label = QLabel(f"{size_label_text}: {size_mb:.2f} MB")

            if self.theme == "dark":
                created_label.setStyleSheet("color: #aaa; font-size: 9pt;")
                modified_label.setStyleSheet("color: #aaa; font-size: 9pt;")
                size_label.setStyleSheet("color: #aaa; font-size: 9pt;")
            else:
                created_label.setStyleSheet("color: #666; font-size: 9pt;")
                modified_label.setStyleSheet("color: #666; font-size: 9pt;")
                size_label.setStyleSheet("color: #666; font-size: 9pt;")

            time_layout.addWidget(created_label)
            time_layout.addWidget(modified_label)
            time_layout.addWidget(size_label)
            time_layout.addStretch()
            time_widget.setLayout(time_layout)

            # 文本区域
            text_widget = QWidget()
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(3)

            title_label = QLabel(self.note_info["name"])
            title_label.setWordWrap(True)
            title_font = title_label.font()
            title_font.setPointSize(10)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

            path_label = QLabel(self.note_info["path"])
            path_label.setWordWrap(True)
            path_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

            # 在标题后面添加置顶标记
            if self.note_info.get("is_pinned", False):
                title_label.setText(f"📌 {self.note_info['name']}")

            if self.theme == "dark":
                title_label.setStyleSheet("color: #ffffff;")
                path_label.setStyleSheet("color: #aaa; font-size: 9pt;")
            else:
                title_label.setStyleSheet("color: #000000;")
                path_label.setStyleSheet("color: #666; font-size: 9pt;")

            text_layout.addWidget(title_label)
            text_layout.addWidget(path_label)
            text_widget.setLayout(text_layout)

            main_layout.addWidget(icon_widget)
            main_layout.addWidget(time_widget)
            main_layout.addWidget(text_widget, 1)
            self.setLayout(main_layout)
        except Exception as e:
            print(f"创建列表项UI错误: {e}")

    def sizeHint(self):
        try:
            layout = self.layout()
            if layout:
                text_widget = layout.itemAt(2).widget()
                if text_widget:
                    title_label = text_widget.layout().itemAt(0).widget()
                    path_label = text_widget.layout().itemAt(1).widget()

                    fm_title = QFontMetrics(title_label.font())
                    fm_path = QFontMetrics(path_label.font())

                    title_width = 400
                    title_height = fm_title.boundingRect(0, 0, title_width, 0,
                                                         Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
                                                         title_label.text()).height()

                    path_width = 400
                    path_height = fm_path.boundingRect(0, 0, path_width, 0,
                                                       Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
                                                       path_label.text()).height()

                    total_height = max(80, title_height + path_height + 30)
                    return QSize(800, total_height)
        except:
            pass
        return QSize(800, 80)


# 网格视图中的笔记项目
class GridItemWidget(QWidget):
    clicked = pyqtSignal(dict)
    rightClicked = pyqtSignal(dict, QPoint)

    def __init__(self, note_info: Dict, theme: str = "light"):
        super().__init__()
        self.note_info = note_info
        self.theme = theme
        self.init_ui()

    def init_ui(self):
        try:
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(5)
            main_layout.setAlignment(Qt.AlignCenter)

            # 图标区域（包含置顶图标）
            icon_widget = QWidget()
            icon_layout = QVBoxLayout()
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_layout.setSpacing(2)

            # 置顶图标（如果笔记已置顶）
            if self.note_info.get("is_pinned", False):
                pin_label = QLabel("📌")
                pin_label.setAlignment(Qt.AlignCenter)
                pin_label.setStyleSheet("font-size: 16px;")
                icon_layout.addWidget(pin_label)

            # 文件图标
            icon_paths = [
                "icons/" + self.note_info.get('icon', 'txt.png'),
                os.path.join(os.path.dirname(__file__), "icons", self.note_info.get('icon', 'txt.png')),
                get_resource_path("icons/" + self.note_info.get('icon', 'txt.png'))
            ]

            pixmap = None
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        pixmap = QPixmap(icon_path)
                        break
                    except:
                        continue

            if pixmap is None or pixmap.isNull():
                pixmap = QPixmap(80, 80)
                pixmap.fill(Qt.lightGray)

            icon_label = QLabel()
            icon_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_label.setAlignment(Qt.AlignCenter)
            icon_layout.addWidget(icon_label)
            icon_widget.setLayout(icon_layout)

            # 文件名
            name_label = QLabel(self.note_info["name"])
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setMinimumHeight(30)

            # 在文件名前添加置顶标记
            if self.note_info.get("is_pinned", False):
                name_label.setText(f"📌 {self.note_info['name']}")

            font = name_label.font()
            font.setPointSize(9)
            font.setBold(True)
            name_label.setFont(font)

            # 类型和大小信息
            ext = self.note_info["type"]
            size_mb = self.note_info["total_size"] / (1024 * 1024)
            size_label_text = "笔记大小" if self.note_info["is_folder"] else "文件大小"
            info_label = QLabel(f"{ext.upper()} | {size_label_text}: {size_mb:.1f}MB")
            info_label.setAlignment(Qt.AlignCenter)

            main_layout.addWidget(icon_widget)
            main_layout.addWidget(name_label)
            main_layout.addWidget(info_label)

            self.setMinimumSize(160, 140)
            self.setMaximumWidth(200)
            self.setLayout(main_layout)
            self.update_style()
        except Exception as e:
            print(f"创建网格项UI错误: {e}")

    def update_style(self):
        try:
            if self.theme == "dark":
                self.setStyleSheet("""
                    QWidget {
                        border: 1px solid #555;
                        border-radius: 8px;
                        background-color: #3c3c3c;
                    }
                    QWidget:hover {
                        border: 2px solid #4CAF50;
                        background-color: #454545;
                    }
                    QLabel {
                        color: #ffffff;
                    }
                """)
            else:
                self.setStyleSheet("""
                    QWidget {
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        background-color: #ffffff;
                    }
                    QWidget:hover {
                        border: 2px solid #4CAF50;
                        background-color: #f0f9f0;
                    }
                    QLabel {
                        color: #000000;
                    }
                """)
        except:
            pass

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                self.clicked.emit(self.note_info)
            elif event.button() == Qt.RightButton:
                self.rightClicked.emit(self.note_info, event.globalPos())
            super().mousePressEvent(event)
        except:
            pass

    def mouseDoubleClickEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                self.clicked.emit(self.note_info)
            super().mouseDoubleClickEvent(event)
        except:
            pass


# 主窗口
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.current_notes = []
        self.filtered_notes = []
        self.current_sort = self.config.data.get("sort_by", "name_asc")
        self.current_view = self.config.data.get("view_mode", "list")
        self.current_theme = self.config.data.get("theme", "light")
        self.scanner = None
        self.tray_icon = None
        self.is_minimized_to_tray = False

        # 设置窗口图标
        self.setWindowIcon(QIcon(self.get_logo_path()))

        # 初始化系统托盘
        self.init_tray_icon()

        self.init_ui()
        QTimer.singleShot(100, self.load_notes)

    def get_logo_path(self):
        """获取logo路径，支持打包后运行"""
        logo_paths = [
            "logo.ico",
            os.path.join(os.path.dirname(__file__), "logo.ico"),
            get_resource_path("logo.ico")
        ]

        for path in logo_paths:
            if os.path.exists(path):
                return path
        return None

    def init_tray_icon(self):
        """初始化系统托盘图标"""
        try:
            # 创建系统托盘图标
            self.tray_icon = QSystemTrayIcon(self)

            # 设置托盘图标
            icon_path = self.get_logo_path()
            if icon_path:
                self.tray_icon.setIcon(QIcon(icon_path))
            else:
                # 如果没有图标，使用默认的图标
                self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

            # 创建托盘菜单
            tray_menu = QMenu()

            # 显示主窗口
            show_action = tray_menu.addAction("显示主窗口")
            show_action.triggered.connect(self.show_from_tray)

            # 分隔线
            tray_menu.addSeparator()

            # 退出程序
            quit_action = tray_menu.addAction("退出")
            quit_action.triggered.connect(self.quit_application)

            # 设置托盘菜单
            self.tray_icon.setContextMenu(tray_menu)

            # 连接托盘图标点击事件
            self.tray_icon.activated.connect(self.tray_icon_activated)

        except Exception as e:
            print(f"初始化托盘图标错误: {e}")

    def tray_icon_activated(self, reason):
        """托盘图标激活事件处理"""
        try:
            # 双击托盘图标显示主窗口
            if reason == QSystemTrayIcon.DoubleClick:
                self.show_from_tray()
            # 在macOS上，可能需要处理其他事件
            elif reason == QSystemTrayIcon.Trigger:
                # 单击显示上下文菜单
                pass
        except Exception as e:
            print(f"托盘图标激活错误: {e}")

    def show_from_tray(self):
        """从托盘恢复显示窗口"""
        try:
            self.showNormal()  # 恢复窗口
            self.activateWindow()  # 激活窗口
            self.raise_()  # 置顶窗口

            if self.tray_icon:
                self.tray_icon.hide()  # 隐藏托盘图标

            self.is_minimized_to_tray = False
            self.statusBar().showMessage("已从托盘恢复")
        except Exception as e:
            print(f"从托盘恢复错误: {e}")

    def hide_to_tray(self):
        """隐藏窗口到托盘"""
        try:
            self.hide()  # 隐藏主窗口

            if self.tray_icon:
                # 显示系统托盘图标
                self.tray_icon.show()

                # 显示通知
                self.tray_icon.showMessage(
                    "森明笔记",
                    "程序已最小化到托盘，点击托盘图标可恢复窗口",
                    QSystemTrayIcon.Information,
                    3000
                )

            self.is_minimized_to_tray = True
        except Exception as e:
            print(f"隐藏到托盘错误: {e}")

    def quit_application(self):
        """退出应用程序"""
        try:
            # 关闭窗口时保存配置
            self.config.data["window_geometry"] = self.saveGeometry().toHex().data().decode()
            self.config.save_config()

            # 停止扫描线程
            if self.scanner and self.scanner.isRunning():
                self.scanner.cancel()
                self.scanner.wait()

            # 隐藏托盘图标
            if self.tray_icon:
                self.tray_icon.hide()

            # 退出应用程序
            QApplication.quit()
        except Exception as e:
            print(f"退出应用程序错误: {e}")
            QApplication.quit()

    def init_ui(self):
        try:
            self.setWindowTitle("森明笔记 msm_bcf_works@163.com")
            self.setGeometry(100, 100, 1200, 800)

            if self.config.data.get("window_geometry"):
                try:
                    self.restoreGeometry(QByteArray.fromHex(self.config.data["window_geometry"].encode()))
                except:
                    pass

            # 创建中心部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            # 主布局
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(10, 10, 10, 10)

            # 顶部工具栏
            toolbar_layout = QHBoxLayout()

            self.search_edit = QLineEdit()
            self.search_edit.setPlaceholderText("搜索笔记...")
            self.search_edit.textChanged.connect(self.filter_notes)
            toolbar_layout.addWidget(self.search_edit)

            settings_btn = QPushButton("⚙ 设置")
            settings_btn.clicked.connect(self.open_settings)
            toolbar_layout.addWidget(settings_btn)

            toolbar_layout.addWidget(QLabel("排序:"))
            self.sort_combo = QComboBox()
            self.sort_combo.addItems([
                "名称 ↑", "名称 ↓",
                "修改时间 ↑", "修改时间 ↓",
                "创建时间 ↑", "创建时间 ↓",
                "大小 ↑", "大小 ↓",
                "类型 ↑", "类型 ↓"
            ])

            sort_map = {
                "name_asc": 0, "name_desc": 1,
                "mod_asc": 2, "mod_desc": 3,
                "create_asc": 4, "create_desc": 5,
                "size_asc": 6, "size_desc": 7,
                "type_asc": 8, "type_desc": 9
            }
            self.sort_combo.setCurrentIndex(sort_map.get(self.current_sort, 0))
            self.sort_combo.currentIndexChanged.connect(self.change_sort)
            toolbar_layout.addWidget(self.sort_combo)

            self.view_toggle_btn = QPushButton()
            self.update_view_button()
            self.view_toggle_btn.clicked.connect(self.toggle_view)
            toolbar_layout.addWidget(self.view_toggle_btn)

            self.theme_toggle_btn = QPushButton("主题: light")
            self.theme_toggle_btn.clicked.connect(self.toggle_theme)
            toolbar_layout.addWidget(self.theme_toggle_btn)

            self.refresh_btn = QPushButton("🔄 刷新")
            self.refresh_btn.clicked.connect(self.refresh_notes)
            toolbar_layout.addWidget(self.refresh_btn)

            toolbar_layout.addStretch()
            main_layout.addLayout(toolbar_layout)

            # 创建视图容器
            self.view_container = QStackedWidget()

            # 列表视图
            self.list_widget = QWidget()
            list_layout = QVBoxLayout(self.list_widget)
            list_layout.setContentsMargins(0, 0, 0, 0)

            self.notes_list = QListWidget()
            self.notes_list.itemDoubleClicked.connect(self.open_note_from_list)
            self.notes_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.notes_list.customContextMenuRequested.connect(self.show_list_context_menu)
            self.notes_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.notes_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            list_layout.addWidget(self.notes_list)

            # 网格视图
            self.grid_widget = QWidget()
            grid_layout = QVBoxLayout(self.grid_widget)
            grid_layout.setContentsMargins(0, 0, 0, 0)

            self.grid_scroll_area = QScrollArea()
            self.grid_scroll_area.setWidgetResizable(True)
            self.grid_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.grid_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.grid_scroll_area.setFrameShape(QFrame.NoFrame)

            self.grid_container = QWidget()
            self.grid_scroll_area.setWidget(self.grid_container)
            self.grid_layout = QGridLayout(self.grid_container)
            self.grid_layout.setAlignment(Qt.AlignTop)
            self.grid_layout.setContentsMargins(15, 15, 15, 15)
            self.grid_layout.setHorizontalSpacing(15)
            self.grid_layout.setVerticalSpacing(15)

            grid_layout.addWidget(self.grid_scroll_area)

            self.view_container.addWidget(self.list_widget)
            self.view_container.addWidget(self.grid_widget)

            if self.current_view == "list":
                self.view_container.setCurrentIndex(0)
            else:
                self.view_container.setCurrentIndex(1)

            self.progress_label = QLabel("就绪")
            self.progress_label.setAlignment(Qt.AlignCenter)

            main_layout.addWidget(self.view_container, 1)
            main_layout.addWidget(self.progress_label)
            central_widget.setLayout(main_layout)

            self.statusBar().showMessage("就绪")
            self.apply_theme(self.current_theme)
        except Exception as e:
            print(f"初始化UI错误: {e}")
            traceback.print_exc()

    def update_view_button(self):
        if self.current_view == "list":
            self.view_toggle_btn.setText("网格视图")
        else:
            self.view_toggle_btn.setText("列表视图")

    def toggle_view(self):
        try:
            self.current_view = "grid" if self.current_view == "list" else "list"
            self.config.data["view_mode"] = self.current_view
            self.config.save_config()
            self.update_view_button()

            if self.current_view == "list":
                self.view_container.setCurrentIndex(0)
            else:
                self.view_container.setCurrentIndex(1)

            notes = self.filtered_notes if self.filtered_notes else self.current_notes
            self.display_notes(notes)
        except Exception as e:
            print(f"切换视图错误: {e}")

    def toggle_theme(self):
        try:
            self.current_theme = "dark" if self.current_theme == "light" else "light"
            self.config.data["theme"] = self.current_theme
            self.config.save_config()
            self.apply_theme(self.current_theme)
            self.theme_toggle_btn.setText(f"主题: {self.current_theme}")

            notes = self.filtered_notes if self.filtered_notes else self.current_notes
            self.display_notes(notes)
        except Exception as e:
            print(f"切换主题错误: {e}")

    def refresh_notes(self):
        # 清空当前笔记列表，重新加载
        self.current_notes = []
        self.filtered_notes = []
        self.load_notes()

    def apply_theme(self, theme):
        try:
            if theme == "dark":
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #1e1e1e;
                    }
                    QWidget {
                        background-color: #2b2b2b;
                        color: #ffffff;
                    }
                    QLineEdit, QComboBox {
                        background-color: #3c3c3c;
                        color: #ffffff;
                        border: 1px solid #555;
                        border-radius: 3px;
                        padding: 5px;
                    }
                    QPushButton {
                        background-color: #3c3c3c;
                        color: #ffffff;
                        border: 1px solid #555;
                        border-radius: 3px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #4c4c4c;
                        border-color: #666;
                    }
                    QListWidget {
                        background-color: transparent;
                        color: #ffffff;
                        border: 1px solid #555;
                        border-radius: 3px;
                    }
                    QScrollArea {
                        background-color: transparent;
                        border: none;
                    }
                    QLabel {
                        color: #ffffff;
                    }
                """)
                self.progress_label.setStyleSheet("color: #ffffff; background-color: transparent;")
            else:
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #f0f0f0;
                    }
                    QWidget {
                        background-color: #f5f5f5;
                        color: #000000;
                    }
                    QLineEdit, QComboBox {
                        background-color: #ffffff;
                        color: #000000;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        padding: 5px;
                    }
                    QPushButton {
                        background-color: #ffffff;
                        color: #000000;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                        border-color: #aaa;
                    }
                    QListWidget {
                        background-color: #ffffff;
                        color: #000000;
                        border: 1px solid #ccc;
                        border-radius: 3px;
                    }
                    QScrollArea {
                        background-color: #f5f5f5;
                        border: none;
                    }
                    QLabel {
                        color: #000000;
                    }
                """)
                self.progress_label.setStyleSheet("color: #000000; background-color: transparent;")
        except Exception as e:
            print(f"应用主题错误: {e}")

    def load_notes(self):
        try:
            notes_folder = self.config.data["notes_folder"]

            if not os.path.exists(notes_folder):
                QMessageBox.warning(self, "警告", f"笔记文件夹不存在:\n{notes_folder}")
                return

            # 如果扫描器正在运行，先停止它
            if self.scanner and self.scanner.isRunning():
                self.scanner.cancel()
                self.scanner.wait()
                self.scanner = None

            # 创建新的扫描器
            self.scanner = FileSystemScanner(notes_folder, self.config)
            self.scanner.scan_progress.connect(self.update_progress)
            self.scanner.scan_complete.connect(self.on_scan_complete)
            self.scanner.start()

            self.statusBar().showMessage("正在扫描笔记...")
        except Exception as e:
            print(f"加载笔记错误: {e}")
            traceback.print_exc()

    def update_progress(self, current, total, filename):
        try:
            self.progress_label.setText(f"扫描中... {current}/{total}: {filename[:30]}")
        except:
            pass

    def on_scan_complete(self, notes):
        try:
            self.current_notes = notes
            self.filter_notes()
            self.statusBar().showMessage(f"找到 {len(notes)} 个笔记")
            self.progress_label.setText(f"找到 {len(notes)} 个笔记")
        except Exception as e:
            print(f"扫描完成处理错误: {e}")

    def filter_notes(self):
        try:
            search_text = self.search_edit.text().lower()

            if not search_text:
                self.filtered_notes = []
                self.display_notes(self.current_notes)
                return

            filtered = []
            for note in self.current_notes:
                if (search_text in note["name"].lower() or
                        search_text in note.get("original_name", "").lower() or
                        search_text in note["path"].lower()):
                    filtered.append(note)

            self.filtered_notes = filtered
            self.display_notes(filtered)
        except Exception as e:
            print(f"过滤笔记错误: {e}")

    def sort_notes(self, notes):
        try:
            reverse = "_desc" in self.current_sort

            if "name" in self.current_sort:
                return sorted(notes, key=lambda x: x["name"].lower(), reverse=reverse)
            elif "mod" in self.current_sort:
                return sorted(notes, key=lambda x: x["modified"], reverse=reverse)
            elif "create" in self.current_sort:
                return sorted(notes, key=lambda x: x["created"], reverse=reverse)
            elif "size" in self.current_sort:
                return sorted(notes, key=lambda x: x["total_size"], reverse=reverse)
            elif "type" in self.current_sort:
                return sorted(notes, key=lambda x: x["type"], reverse=reverse)

            return notes
        except Exception as e:
            print(f"排序笔记错误: {e}")
            return notes

    def display_notes(self, notes):
        try:
            if self.current_view == "list":
                self.refresh_list_view(notes)
            else:
                self.refresh_grid_view(notes)
        except Exception as e:
            print(f"显示笔记错误: {e}")
            traceback.print_exc()

    def refresh_list_view(self, notes):
        """刷新列表视图"""
        try:
            if not notes:
                self.notes_list.clear()
                return

            # 分离置顶和非置顶笔记
            pinned_notes = []
            unpinned_notes = []

            for note in notes:
                if note.get("is_pinned", False):
                    pinned_notes.append(note)
                else:
                    unpinned_notes.append(note)

            # 分别排序
            sorted_pinned = self.sort_notes(pinned_notes)
            sorted_unpinned = self.sort_notes(unpinned_notes)

            # 合并列表：置顶笔记在前，非置顶笔记在后
            sorted_notes = sorted_pinned + sorted_unpinned

            # 清空列表
            self.notes_list.clear()

            # 重新添加所有笔记
            for note in sorted_notes:
                item_widget = CustomListWidgetItem(note, self.current_theme)
                item = QListWidgetItem(self.notes_list)
                item.setSizeHint(item_widget.sizeHint())
                item.setData(Qt.UserRole, note)
                self.notes_list.addItem(item)
                self.notes_list.setItemWidget(item, item_widget)

        except Exception as e:
            print(f"刷新列表视图错误: {e}")
            traceback.print_exc()

    def refresh_grid_view(self, notes):
        """刷新网格视图"""
        try:
            if not notes:
                # 清空现有网格
                for i in reversed(range(self.grid_layout.count())):
                    item = self.grid_layout.itemAt(i)
                    if item:
                        widget = item.widget()
                        if widget:
                            widget.deleteLater()
                return

            # 分离置顶和非置顶笔记
            pinned_notes = []
            unpinned_notes = []

            for note in notes:
                if note.get("is_pinned", False):
                    pinned_notes.append(note)
                else:
                    unpinned_notes.append(note)

            # 分别排序
            sorted_pinned = self.sort_notes(pinned_notes)
            sorted_unpinned = self.sort_notes(unpinned_notes)

            # 合并列表：置顶笔记在前，非置顶笔记在后
            sorted_notes = sorted_pinned + sorted_unpinned

            # 清空现有网格
            for i in reversed(range(self.grid_layout.count())):
                item = self.grid_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

            # 重新创建网格
            container_width = self.grid_scroll_area.viewport().width() - 30
            item_width = 180
            items_per_row = max(1, container_width // item_width)

            row = 0
            col = 0

            for note in sorted_notes:
                item_widget = GridItemWidget(note, self.current_theme)
                item_widget.clicked.connect(self.open_note_from_grid)
                item_widget.rightClicked.connect(lambda n=note, pos=None: self.show_grid_context_menu(n, pos))

                self.grid_layout.addWidget(item_widget, row, col)

                col += 1
                if col >= items_per_row:
                    col = 0
                    row += 1

            self.grid_layout.setRowStretch(row + 1, 1)

        except Exception as e:
            print(f"刷新网格视图错误: {e}")
            traceback.print_exc()

    def open_note_from_list(self, item):
        try:
            if isinstance(item, QListWidgetItem):
                note_info = item.data(Qt.UserRole)
                if note_info:
                    self.open_note_internal(note_info)
        except Exception as e:
            print(f"从列表打开笔记错误: {e}")

    def open_note_from_grid(self, note_info):
        try:
            self.open_note_internal(note_info)
        except Exception as e:
            print(f"从网格打开笔记错误: {e}")

    def open_note_internal(self, note_info):
        try:
            file_path = note_info["path"]
            file_type = note_info["type"]

            file_type_info = self.config.get_file_type_info(file_type)
            if not file_type_info:
                QMessageBox.warning(
                    self,
                    "文件类型不支持",
                    f"文件类型 '{file_type}' 当前不受支持。\n\n"
                    f"请在设置中添加 '{file_type}' 类型的支持。"
                )
                return

            external_tool = file_type_info.get("external", "")

            if not os.path.exists(file_path):
                QMessageBox.warning(self, "错误", f"文件不存在:\n{file_path}")
                return

            if not external_tool:
                QMessageBox.warning(
                    self,
                    "未配置打开方式",
                    f"文件类型 '{file_type}' 没有配置默认打开方式。\n\n"
                    f"请在设置中添加 '{file_type}' 类型的外部工具路径。"
                )
                return

            self.open_with_external(file_path, external_tool)
        except Exception as e:
            print(f"打开笔记内部错误: {e}")

    def open_with_external(self, file_path, external_tool):
        try:
            if sys.platform == "win32":
                if external_tool and os.path.exists(external_tool):
                    # 使用shell=True确保路径中的特殊字符被正确处理
                    subprocess.Popen([external_tool, file_path], shell=True)
                    self.statusBar().showMessage(f"使用 {os.path.basename(external_tool)} 打开文件")
                else:
                    try:
                        os.startfile(file_path)
                        self.statusBar().showMessage("使用系统默认程序打开文件")
                    except:
                        QMessageBox.warning(self, "错误", f"无法找到指定的外部工具:\n{external_tool}")
            else:
                if external_tool and os.path.exists(external_tool):
                    subprocess.Popen([external_tool, file_path])
                else:
                    if sys.platform == "darwin":
                        subprocess.Popen(["open", file_path])
                    else:
                        subprocess.Popen(["xdg-open", file_path])

                self.statusBar().showMessage(f"使用外部工具打开文件")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法使用外部工具打开:\n{str(e)}")

    def show_list_context_menu(self, position):
        try:
            item = self.notes_list.itemAt(position)
            if not item:
                return

            note_info = item.data(Qt.UserRole)
            if not note_info:
                return

            self.show_context_menu(note_info, self.notes_list.mapToGlobal(position))
        except Exception as e:
            print(f"显示列表右键菜单错误: {e}")

    def show_grid_context_menu(self, note_info, position):
        try:
            self.show_context_menu(note_info, position)
        except Exception as e:
            print(f"显示网格右键菜单错误: {e}")

    def show_context_menu(self, note_info, position):
        try:
            menu = QMenu()

            if self.current_theme == "dark":
                menu.setStyleSheet("""
                    QMenu {
                        background-color: #3c3c3c;
                        color: white;
                        border: 1px solid #555;
                    }
                    QMenu::item {
                        padding: 5px 20px;
                    }
                    QMenu::item:selected {
                        background-color: #4c4c4c;
                    }
                """)
            else:
                menu.setStyleSheet("""
                    QMenu {
                        background-color: white;
                        color: black;
                        border: 1px solid #ccc;
                    }
                    QMenu::item {
                        padding: 5px 20px;
                    }
                    QMenu::item:selected {
                        background-color: #f0f0f0;
                    }
                """)

            open_action = menu.addAction("打开")
            show_in_explorer = menu.addAction("在文件资源管理器中显示")

            # 添加置顶/取消置顶菜单项
            if note_info.get("is_pinned", False):
                pin_action = menu.addAction("取消置顶")
            else:
                pin_action = menu.addAction("置顶")

            action = menu.exec_(position)

            if action == open_action:
                self.open_note_internal(note_info)
            elif action == show_in_explorer:
                self.show_in_explorer(note_info)
            elif action == pin_action:
                self.toggle_pin_status(note_info)
        except Exception as e:
            print(f"显示右键菜单错误: {e}")

    def toggle_pin_status(self, note_info):
        """切换笔记的置顶状态"""
        try:
            file_path = note_info["path"]

            if note_info.get("is_pinned", False):
                # 当前是置顶状态，取消置顶
                if self.config.unpin_note(file_path):
                    note_info["is_pinned"] = False
                    self.statusBar().showMessage(f"已取消置顶: {note_info['name']}")

                    # 更新所有笔记的置顶状态
                    self.update_all_notes_pinned_status()

                    # 刷新显示
                    notes = self.filtered_notes if self.filtered_notes else self.current_notes
                    self.display_notes(notes)
                else:
                    QMessageBox.warning(self, "错误", "取消置顶失败")
            else:
                # 当前不是置顶状态，置顶
                if self.config.pin_note(file_path):
                    note_info["is_pinned"] = True
                    self.statusBar().showMessage(f"已置顶: {note_info['name']}")

                    # 更新所有笔记的置顶状态
                    self.update_all_notes_pinned_status()

                    # 刷新显示
                    notes = self.filtered_notes if self.filtered_notes else self.current_notes
                    self.display_notes(notes)
                else:
                    QMessageBox.warning(self, "错误", "置顶失败")
        except Exception as e:
            print(f"切换置顶状态错误: {e}")
            QMessageBox.warning(self, "错误", f"操作失败: {str(e)}")

    def update_all_notes_pinned_status(self):
        """更新所有笔记的置顶状态"""
        try:
            # 更新当前笔记列表中的置顶状态
            for note in self.current_notes:
                note["is_pinned"] = self.config.is_note_pinned(note["path"])

            # 更新过滤后的笔记列表中的置顶状态
            for note in self.filtered_notes:
                note["is_pinned"] = self.config.is_note_pinned(note["path"])
        except Exception as e:
            print(f"更新笔记置顶状态错误: {e}")

    def show_in_explorer(self, note_info):
        """在文件资源管理器中显示文件（选中文件）"""
        try:
            file_path = note_info["path"]

            if sys.platform == "win32":
                # 在Windows上，使用explorer /select命令来选中文件
                # 确保路径是绝对路径且规范化
                abs_path = os.path.abspath(file_path)

                # 方法1：使用subprocess.run并正确转义路径
                try:
                    # 使用双引号将路径括起来，确保特殊字符被正确处理
                    cmd = f'explorer /select, "{abs_path}"'

                    # 使用shell=True来执行命令，这样Windows命令行解释器会正确处理路径
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                    if result.returncode != 0:
                        # 如果失败，尝试使用其他方法
                        raise Exception(f"命令执行失败: {result.stderr}")

                    return
                except Exception as e:
                    print(f"方法1失败: {e}")

                    # 方法2：尝试使用不同的命令格式
                    try:
                        # 使用os.startfile打开文件夹
                        folder = os.path.dirname(abs_path)
                        os.startfile(folder)
                    except Exception as e2:
                        print(f"方法2失败: {e2}")

                        # 方法3：使用QDesktopServices打开文件夹
                        try:
                            folder = os.path.dirname(abs_path)
                            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
                        except Exception as e3:
                            print(f"方法3失败: {e3}")
                            QMessageBox.warning(self, "错误",
                                                f"无法在资源管理器中显示文件:\n{str(e)}\n\n尝试打开了文件夹。")
            else:
                # 在其他操作系统上，打开文件所在的文件夹
                folder = os.path.dirname(file_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

        except Exception as e:
            print(f"在资源管理器显示错误: {e}")
            QMessageBox.warning(self, "错误", f"无法在资源管理器中显示文件:\n{str(e)}")

    def change_sort(self, index):
        try:
            sort_map = [
                "name_asc", "name_desc",
                "mod_asc", "mod_desc",
                "create_asc", "create_desc",
                "size_asc", "size_desc",
                "type_asc", "type_desc"
            ]

            if index < len(sort_map):
                self.current_sort = sort_map[index]
                self.config.data["sort_by"] = self.current_sort
                self.config.save_config()

                notes = self.filtered_notes if self.filtered_notes else self.current_notes
                self.display_notes(notes)
        except Exception as e:
            print(f"改变排序方式错误: {e}")

    def open_settings(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, \
            QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
        from PyQt5.QtCore import Qt

        class SettingsDialog(QDialog):
            def __init__(self, config, theme="light"):
                super().__init__()
                self.config = config
                self.theme = theme
                self.init_ui()
                self.apply_theme(theme)

            def init_ui(self):
                self.setWindowTitle("设置 - 森明笔记")
                self.setFixedSize(600, 500)

                layout = QVBoxLayout()

                folder_group = QGroupBox("笔记文件夹设置")
                folder_layout = QVBoxLayout()

                folder_hbox = QHBoxLayout()
                self.folder_edit = QLineEdit(self.config.data["notes_folder"])
                folder_btn = QPushButton("浏览...")
                folder_btn.clicked.connect(self.browse_folder)

                folder_hbox.addWidget(QLabel("笔记总文件夹:"))
                folder_hbox.addWidget(self.folder_edit, 1)
                folder_hbox.addWidget(folder_btn)
                folder_layout.addLayout(folder_hbox)

                folder_group.setLayout(folder_layout)

                # 程序行为设置
                behavior_group = QGroupBox("程序行为设置")
                behavior_layout = QVBoxLayout()

                behavior_hbox = QHBoxLayout()
                behavior_hbox.addWidget(QLabel("关闭窗口按钮行为:"))

                self.close_action_combo = QComboBox()
                self.close_action_combo.addItems(["隐藏到托盘", "直接退出程序"])

                # 设置当前选择
                close_action = self.config.data.get("close_action", "hide_to_tray")
                if close_action == "hide_to_tray":
                    self.close_action_combo.setCurrentIndex(0)
                else:
                    self.close_action_combo.setCurrentIndex(1)

                behavior_hbox.addWidget(self.close_action_combo)
                behavior_hbox.addStretch()

                behavior_layout.addLayout(behavior_hbox)
                behavior_group.setLayout(behavior_layout)

                type_group = QGroupBox("文件类型设置")
                type_layout = QVBoxLayout()

                self.type_table = QTableWidget()
                self.type_table.setColumnCount(3)
                self.type_table.setHorizontalHeaderLabels(["扩展名", "图标", "外部工具路径"])
                self.type_table.setAlternatingRowColors(True)

                self.load_file_types_to_table()

                btn_layout = QHBoxLayout()
                add_btn = QPushButton("添加")
                add_btn.clicked.connect(self.add_file_type)
                remove_btn = QPushButton("删除")
                remove_btn.clicked.connect(self.remove_file_type)

                btn_layout.addWidget(add_btn)
                btn_layout.addWidget(remove_btn)
                btn_layout.addStretch()

                type_layout.addWidget(self.type_table)
                type_layout.addLayout(btn_layout)
                type_group.setLayout(type_layout)

                button_layout = QHBoxLayout()
                save_btn = QPushButton("保存全部")
                save_btn.clicked.connect(self.save_all)
                cancel_btn = QPushButton("取消")
                cancel_btn.clicked.connect(self.reject)

                button_layout.addStretch()
                button_layout.addWidget(save_btn)
                button_layout.addWidget(cancel_btn)

                layout.addWidget(folder_group)
                layout.addWidget(behavior_group)  # 添加行为设置组
                layout.addWidget(type_group)
                layout.addLayout(button_layout)

                self.setLayout(layout)

            def apply_theme(self, theme):
                if theme == "dark":
                    self.setStyleSheet("""
                        QDialog {
                            background-color: #2b2b2b;
                            color: #ffffff;
                        }
                        QGroupBox {
                            background-color: #3c3c3c;
                            color: #ffffff;
                            border: 1px solid #555;
                            border-radius: 5px;
                            margin-top: 10px;
                            padding-top: 10px;
                        }
                        QGroupBox::title {
                            subcontrol-origin: margin;
                            left: 10px;
                            padding: 0 5px;
                        }
                        QLabel {
                            color: #ffffff;
                        }
                        QLineEdit, QTableWidget, QComboBox {
                            background-color: #3c3c3c;
                            color: #ffffff;
                            border: 1px solid #555;
                        }
                        QPushButton {
                            background-color: #3c3c3c;
                            color: #ffffff;
                            border: 1px solid #555;
                            border-radius: 3px;
                            padding: 5px 10px;
                        }
                        QPushButton:hover {
                            background-color: #4c4c4c;
                        }
                    """)
                else:
                    self.setStyleSheet("""
                        QDialog {
                            background-color: #f5f5f5;
                            color: #000000;
                        }
                        QGroupBox {
                            background-color: #ffffff;
                            color: #000000;
                            border: 1px solid #ccc;
                            border-radius: 5px;
                            margin-top: 10px;
                            padding-top: 10px;
                        }
                        QGroupBox::title {
                            subcontrol-origin: margin;
                            left: 10px;
                            padding: 0 5px;
                        }
                        QLabel {
                            color: #000000;
                        }
                        QLineEdit, QTableWidget, QComboBox {
                            background-color: #ffffff;
                            color: #000000;
                            border: 1px solid #ccc;
                        }
                        QPushButton {
                            background-color: #ffffff;
                            color: #000000;
                            border: 1px solid #ccc;
                            border-radius: 3px;
                            padding: 5px 10px;
                        }
                        QPushButton:hover {
                            background-color: #f0f0f0;
                        }
                    """)

            def browse_folder(self):
                folder = QFileDialog.getExistingDirectory(self, "选择笔记文件夹", self.folder_edit.text())
                if folder:
                    self.folder_edit.setText(folder)

            def load_file_types_to_table(self):
                self.type_table.setRowCount(len(self.config.data["file_types"]))

                for i, (type_str, info) in enumerate(self.config.data["file_types"].items()):
                    ext_item = QTableWidgetItem(type_str)
                    self.type_table.setItem(i, 0, ext_item)

                    icon_item = QTableWidgetItem(info.get("icon", "txt.png"))
                    self.type_table.setItem(i, 1, icon_item)

                    path_item = QTableWidgetItem(info.get("external", ""))
                    self.type_table.setItem(i, 2, path_item)

            def add_file_type(self):
                row = self.type_table.rowCount()
                self.type_table.insertRow(row)

                ext_item = QTableWidgetItem("新扩展名")
                self.type_table.setItem(row, 0, ext_item)

                icon_item = QTableWidgetItem("txt.png")
                self.type_table.setItem(row, 1, icon_item)

                path_item = QTableWidgetItem("")
                self.type_table.setItem(row, 2, path_item)

            def remove_file_type(self):
                row = self.type_table.currentRow()
                if row >= 0:
                    self.type_table.removeRow(row)

            def save_all(self):
                self.config.data["notes_folder"] = self.folder_edit.text()

                # 保存关闭按钮行为设置
                close_action_index = self.close_action_combo.currentIndex()
                if close_action_index == 0:
                    self.config.data["close_action"] = "hide_to_tray"
                else:
                    self.config.data["close_action"] = "quit"

                new_file_types = {}
                for row in range(self.type_table.rowCount()):
                    type_str = self.type_table.item(row, 0).text()
                    icon = self.type_table.item(row, 1).text()
                    external = self.type_table.item(row, 2).text()

                    new_file_types[type_str] = {
                        "icon": icon,
                        "external": external
                    }

                self.config.data["file_types"] = new_file_types

                if self.config.save_config():
                    QMessageBox.information(self, "成功", "设置已保存！")
                    self.accept()
                else:
                    QMessageBox.warning(self, "错误", "保存设置失败！")

        try:
            dialog = SettingsDialog(self.config, self.current_theme)
            if dialog.exec_() == QDialog.Accepted:
                # 清空当前笔记列表，强制重新扫描
                self.current_notes = []
                self.filtered_notes = []
                self.load_notes()
        except Exception as e:
            print(f"打开设置错误: {e}")

    def closeEvent(self, event):
        """重写关闭事件，根据配置决定行为"""
        try:
            # 保存窗口位置和大小
            self.config.data["window_geometry"] = self.saveGeometry().toHex().data().decode()
            self.config.save_config()

            # 停止扫描线程
            if self.scanner and self.scanner.isRunning():
                self.scanner.cancel()
                self.scanner.wait()

            # 获取配置中的关闭行为
            close_action = self.config.data.get("close_action", "hide_to_tray")

            if close_action == "hide_to_tray":
                # 隐藏到托盘
                self.hide_to_tray()
                event.ignore()
            else:
                # 直接退出程序
                if self.tray_icon:
                    self.tray_icon.hide()
                event.accept()

        except Exception as e:
            print(f"关闭事件错误: {e}")
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            if self.current_view == "grid":
                notes = self.filtered_notes if self.filtered_notes else self.current_notes
                if notes:
                    self.display_notes(notes)
        except:
            pass


def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"未捕获的异常:\n{tb}")

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText("程序发生未捕获的异常")
    msg.setInformativeText(str(exc_value))
    msg.setWindowTitle("错误")
    msg.setDetailedText(tb)
    msg.exec_()

    sys.__excepthook__(exc_type, exc_value, exc_tb)


def main():
    sys.excepthook = excepthook

    app = QApplication(sys.argv)
    app.setApplicationName("森明笔记")
    app.setOrganizationName("msm_bcf_works")

    # 设置高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    try:
        # 创建必要的图标文件夹
        icons_dir = "icons"
        if not os.path.exists(icons_dir):
            os.makedirs(icons_dir, exist_ok=True)
            print("创建了icons文件夹，请将图标文件放入其中")

        # 创建主窗口
        window = MainWindow()
        window.show()

        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序启动错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()