#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import traceback
import subprocess
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)
            kernel32.FreeConsole()
    except:
        pass

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def validate_windows_name(name, is_folder=False):
    if not name or name.strip() == "":
        return False, "名称不能为空"
    stripped = name.strip()
    if stripped != name:
        return False, "名称不能以空格开头或结尾"
    if name.endswith('.'):
        return False, "名称不能以点结尾"
    forbidden = r'<>:"/\|?*'
    if any(c in name for c in forbidden):
        return False, f"名称不能包含以下字符: {forbidden}"
    reserved = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
                "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]
    if name.upper() in reserved:
        return False, f"名称不能是Windows保留设备名: {name}"
    if len(name) > 255:
        return False, "名称长度不能超过255个字符"
    return True, ""


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
        "close_action": "hide_to_tray",
        "auto_start": False,
        "pinned_notes": []
    }

    def __init__(self, config_path="config.json"):
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_path = os.path.join(exe_dir, config_path)
        self.config_path = config_path
        self.data = self.load_config()
        if self.data.get("theme") == "default":
            self.data["theme"] = "light"
        self._validate_file_types()
        if "close_action" not in self.data:
            self.data["close_action"] = self.DEFAULT_CONFIG["close_action"]
        if "auto_start" not in self.data:
            self.data["auto_start"] = self.DEFAULT_CONFIG["auto_start"]
        if "pinned_notes" not in self.data:
            self.data["pinned_notes"] = self.DEFAULT_CONFIG["pinned_notes"].copy()
        self._apply_auto_start()

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
            self._apply_auto_start()
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

    def _validate_file_types(self):
        if "file_types" not in self.data:
            self.data["file_types"] = self.DEFAULT_CONFIG["file_types"].copy()
        else:
            seen_extensions = set()
            clean_file_types = {}
            for type_str, info in self.data["file_types"].items():
                extensions = [ext.strip().lower() for ext in type_str.split(',')]
                unique_extensions = []
                for ext in extensions:
                    if ext and ext not in seen_extensions:
                        seen_extensions.add(ext)
                        unique_extensions.append(ext)
                if unique_extensions:
                    new_type_str = ','.join(unique_extensions)
                    clean_file_types[new_type_str] = info
            self.data["file_types"] = clean_file_types

    def _get_all_extensions(self) -> Set[str]:
        extensions = set()
        for types in self.data["file_types"].keys():
            for ext in [t.strip().lower() for t in types.split(',')]:
                if ext:
                    extensions.add(ext.lower())
        return extensions

    def get_file_type_info(self, extension: str) -> Optional[Dict]:
        extension = extension.lower().lstrip('.')
        for types, info in self.data["file_types"].items():
            type_list = [t.strip().lower() for t in types.split(',')]
            if extension in type_list:
                return info.copy()
        return None

    def is_supported_extension(self, extension: str) -> bool:
        extension = extension.lower().lstrip('.')
        for types in self.data["file_types"].keys():
            type_list = [t.strip().lower() for t in types.split(',')]
            if extension in type_list:
                return True
        return False

    def is_note_pinned(self, note_path: str) -> bool:
        abs_path = os.path.abspath(note_path)
        return abs_path in self.data["pinned_notes"]

    def pin_note(self, note_path: str) -> bool:
        try:
            abs_path = os.path.abspath(note_path)
            if abs_path not in self.data["pinned_notes"]:
                self.data["pinned_notes"].append(abs_path)
                return self.save_config()
            return True
        except Exception as e:
            print(f"置顶失败: {e}")
            return False

    def unpin_note(self, note_path: str) -> bool:
        try:
            abs_path = os.path.abspath(note_path)
            if abs_path in self.data["pinned_notes"]:
                self.data["pinned_notes"].remove(abs_path)
                return self.save_config()
            return True
        except Exception as e:
            print(f"取消置顶失败: {e}")
            return False

    def _apply_auto_start(self):
        try:
            if sys.platform == "win32":
                self._apply_windows_auto_start()
        except Exception as e:
            print(f"应用自启动失败: {e}")

    def _apply_windows_auto_start(self):
        try:
            import winreg
            exe_path = sys.executable
            if not exe_path.endswith('.exe'):
                exe_path = os.path.abspath(sys.argv[0])
                if not exe_path.endswith('.exe'):
                    return
            cmd = f'"{exe_path}" --minimized'
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "SenMingNotes"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
            if self.data["auto_start"]:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Windows自启动失败: {e}")


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
                        note_info = self._get_folder_note_info(item)
                        if note_info:
                            notes.append(note_info)
                    elif item.is_file():
                        note_info = self._get_file_note_info(item)
                        if note_info:
                            notes.append(note_info)
                except Exception as e:
                    print(f"处理 {item.name} 出错: {e}")
                time.sleep(0.001)
        except Exception as e:
            print(f"扫描目录出错: {e}")
        return notes

    def _get_folder_note_info(self, item) -> Optional[Dict]:
        try:
            folder_path = item.path
            folder_name = item.name
            main_file = self._find_main_file_in_folder(folder_path)
            if main_file:
                ext = os.path.splitext(main_file)[1].lower().lstrip('.')
                file_type_info = self.config.get_file_type_info(ext)
                if not file_type_info:
                    return None
                folder_size = self._calculate_folder_size(folder_path)
                stat = os.stat(main_file)
                return {
                    "name": folder_name,
                    "original_name": folder_name,
                    "path": main_file,
                    "is_folder": True,
                    "folder_path": folder_path,
                    "total_size": folder_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "type": ext,
                    "icon": file_type_info.get("icon", "folder.png"),
                    "is_pinned": self.config.is_note_pinned(main_file)
                }
            return None
        except Exception as e:
            print(f"获取文件夹笔记信息错误: {e}")
            return None

    def _get_file_note_info(self, item) -> Optional[Dict]:
        try:
            ext = os.path.splitext(item.name)[1].lower().lstrip('.')
            if self.config.is_supported_extension(ext):
                file_type_info = self.config.get_file_type_info(ext)
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
                    "is_pinned": self.config.is_note_pinned(item.path)
                }
            return None
        except Exception as e:
            print(f"获取文件笔记信息错误: {e}")
            return None

    def _calculate_folder_size(self, folder_path: str) -> int:
        total = 0
        try:
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except:
                        continue
        except:
            pass
        return total

    def _find_main_file_in_folder(self, folder_path: str) -> Optional[str]:
        try:
            supported_extensions = self.config._get_all_extensions()
            supported_files = []
            for item in os.scandir(folder_path):
                if item.is_file():
                    ext = os.path.splitext(item.name)[1].lower().lstrip('.')
                    if ext in supported_extensions:
                        supported_files.append((item.path, item.name, ext))
            if supported_files:
                folder_name = os.path.basename(folder_path)
                for file_path, filename, ext in supported_files:
                    if os.path.splitext(filename)[0].lower() == folder_name.lower():
                        return file_path
                priority_names = ["index", "main", "readme"]
                for name in priority_names:
                    for file_path, filename, ext in supported_files:
                        if os.path.splitext(filename)[0].lower() == name:
                            return file_path
                return supported_files[0][0]
            return None
        except Exception as e:
            print(f"查找主文件错误: {e}")
            return None


class CustomListWidgetItem(QWidget):
    def __init__(self, note_info: Dict, theme: str = "light"):
        super().__init__()
        self.note_info = note_info
        self.theme = theme
        self.list_item = None
        self.init_ui()

    def init_ui(self):
        try:
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(8, 8, 8, 8)
            main_layout.setSpacing(10)

            icon_label = QLabel()
            icon_label.setFixedSize(48, 48)
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
                for lbl in (created_label, modified_label, size_label):
                    lbl.setStyleSheet("color: #aaa; font-size: 9pt;")
            else:
                for lbl in (created_label, modified_label, size_label):
                    lbl.setStyleSheet("color: #666; font-size: 9pt;")
            time_layout.addWidget(created_label)
            time_layout.addWidget(modified_label)
            time_layout.addWidget(size_label)
            time_layout.addStretch()
            time_widget.setLayout(time_layout)

            text_widget = QWidget()
            text_layout = QVBoxLayout()
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(3)
            if self.note_info.get("is_pinned", False):
                title_text = f"📌 {self.note_info['name']}"
            else:
                title_text = self.note_info["name"]
            title_label = QLabel(title_text)
            title_label.setWordWrap(True)
            title_font = title_label.font()
            title_font.setPointSize(10)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            path_label = QLabel(self.note_info["path"])
            path_label.setWordWrap(True)
            path_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            if self.theme == "dark":
                title_label.setStyleSheet("color: #ffffff;")
                path_label.setStyleSheet("color: #aaa; font-size: 9pt;")
            else:
                title_label.setStyleSheet("color: #000000;")
                path_label.setStyleSheet("color: #666; font-size: 9pt;")
            text_layout.addWidget(title_label)
            text_layout.addWidget(path_label)
            text_widget.setLayout(text_layout)

            main_layout.addWidget(icon_label)
            main_layout.addWidget(time_widget)
            main_layout.addWidget(text_widget, 1)
            self.setLayout(main_layout)
        except Exception as e:
            print(f"创建列表项UI错误: {e}")

    def sizeHint(self):
        return self.layout().sizeHint()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.list_item:
            self.list_item.setSizeHint(self.sizeHint())
            list_widget = self.list_item.listWidget()
            if list_widget:
                list_widget.scheduleDelayedItemsLayout()


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
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(3)
            main_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

            icon_label = QLabel()
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
            icon_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_label.setAlignment(Qt.AlignCenter)

            if self.note_info.get("is_pinned", False):
                name_text = f"📌 {self.note_info['name']}"
            else:
                name_text = self.note_info["name"]
            name_label = QLabel(name_text)
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
            name_label.setMinimumHeight(24)
            font = name_label.font()
            font.setPointSize(9)
            font.setBold(True)
            name_label.setFont(font)

            ext = self.note_info["type"]
            size_mb = self.note_info["total_size"] / (1024 * 1024)
            size_label_text = "笔记大小" if self.note_info["is_folder"] else "文件大小"
            info_label = QLabel(f"{ext.upper()} | {size_label_text}: {size_mb:.1f}MB")
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setWordWrap(True)

            main_layout.addWidget(icon_label)
            main_layout.addWidget(name_label)
            main_layout.addWidget(info_label)
            main_layout.addStretch()

            self.setMinimumWidth(130)
            self.setMaximumWidth(160)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
            self.setLayout(main_layout)
            self.update_style()
        except Exception as e:
            print(f"创建网格项UI错误: {e}")

    def update_style(self):
        try:
            if self.theme == "dark":
                self.setStyleSheet("""
                    QWidget { border: 1px solid #555; border-radius: 8px; background-color: #3c3c3c; }
                    QWidget:hover { border: 2px solid #4CAF50; background-color: #454545; }
                    QLabel { color: #ffffff; }
                """)
            else:
                self.setStyleSheet("""
                    QWidget { border: 1px solid #ddd; border-radius: 8px; background-color: #ffffff; }
                    QWidget:hover { border: 2px solid #4CAF50; background-color: #f0f9f0; }
                    QLabel { color: #000000; }
                """)
        except:
            pass

    def sizeHint(self):
        return self.layout().sizeHint()

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


class MDRedundantDialog(QDialog):
    IMAGE_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.ico',
        '.tiff', '.tif', '.jfif', '.pjpeg', '.pjp', '.apng', '.avif',
        '.heif', '.heic', '.raw', '.cr2', '.nef', '.orf', '.sr2',
        '.psd', '.eps', '.pcx', '.tga', '.wdp', '.hdp', '.jxr'
    }

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.unreferenced_images = []
        self.setWindowTitle("MD未引用图片检查 - 森明笔记")
        self.setMinimumSize(700, 500)
        self.init_ui()
        self.md_path_edit.setText(self.config.data.get("notes_folder", ""))

    def init_ui(self):
        layout = QVBoxLayout(self)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("MD文件/文件夹:"))
        self.md_path_edit = QLineEdit()
        row1.addWidget(self.md_path_edit, 1)
        btn_browse_file = QPushButton("选择文件")
        btn_browse_file.clicked.connect(self.browse_md_file)
        row1.addWidget(btn_browse_file)
        btn_browse_folder = QPushButton("扫描文件夹")
        btn_browse_folder.clicked.connect(self.browse_folder)
        row1.addWidget(btn_browse_folder)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("目标目录:"))
        self.dest_edit = QLineEdit()
        row2.addWidget(self.dest_edit, 1)
        btn_browse_dest = QPushButton("选择目录")
        btn_browse_dest.clicked.connect(self.browse_dest)
        row2.addWidget(btn_browse_dest)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.btn_check = QPushButton("检查")
        self.btn_check.clicked.connect(self.check_md)
        row3.addWidget(self.btn_check)
        self.btn_move = QPushButton("移动")
        self.btn_move.clicked.connect(self.move_images)
        row3.addWidget(self.btn_move)
        self.btn_delete = QPushButton("删除")
        self.btn_delete.clicked.connect(self.delete_images)
        row3.addWidget(self.btn_delete)
        row3.addStretch()
        layout.addLayout(row3)

        self.text_display = QPlainTextEdit()
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)

        self.apply_theme()

    def apply_theme(self):
        theme = self.config.data.get("theme", "light")
        if theme == "dark":
            self.setStyleSheet("""
                QDialog { background-color: #2b2b2b; color: #ffffff; }
                QLineEdit, QPlainTextEdit { background-color: #3c3c3c; border: 1px solid #555; color: #ffffff; }
                QPushButton { background-color: #3c3c3c; border: 1px solid #555; padding: 5px 10px; color: #ffffff; }
                QPushButton:hover { background-color: #4c4c4c; }
                QLabel { color: #ffffff; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #f5f5f5; color: #000000; }
                QLineEdit, QPlainTextEdit { background-color: #ffffff; border: 1px solid #ccc; }
                QPushButton { background-color: #ffffff; border: 1px solid #ccc; padding: 5px 10px; }
                QPushButton:hover { background-color: #f0f0f0; }
                QLabel { color: #000000; }
            """)

    def _log(self, msg):
        self.text_display.appendPlainText(msg)

    def _clear_log(self):
        self.text_display.clear()

    def _is_image_file(self, filename):
        _, ext = os.path.splitext(filename)
        return ext.lower() in self.IMAGE_EXTENSIONS

    def _extract_referenced_basenames(self, md_content):
        basenames = set()
        md_pattern = r'!\[.*?\]\((.*?)\)'
        html_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        urls = re.findall(md_pattern, md_content, re.IGNORECASE)
        urls += re.findall(html_pattern, md_content, re.IGNORECASE)
        for url in urls:
            if url.startswith(('http://', 'https://', '//')):
                continue
            clean = url.split('?')[0].split('#')[0]
            basename = os.path.basename(clean)
            if basename:
                basenames.add(basename)
        return basenames

    def browse_md_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Markdown文件", "",
            "Markdown文件 (*.md);;所有文件 (*.*)"
        )
        if file_path:
            self.md_path_edit.setText(file_path)

    def browse_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择包含Markdown文件的文件夹")
        if dir_path:
            self.md_path_edit.setText(dir_path)

    def browse_dest(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if dir_path:
            self.dest_edit.setText(dir_path)

    def check_md(self):
        self._clear_log()
        self.unreferenced_images = []

        path = self.md_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "提示", "请输入或选择一个MD文件或文件夹")
            return

        if os.path.isdir(path):
            self._check_folder(path)
        elif os.path.isfile(path) and path.lower().endswith('.md'):
            self._check_single_file(path)
        else:
            QMessageBox.warning(self, "提示", "路径无效，请输入有效的 .md 文件路径或文件夹路径")

    def _check_single_file(self, md_path):
        self._log(f"检查文件: {md_path}")
        md_dir = os.path.dirname(os.path.abspath(md_path))
        md_basename = os.path.basename(md_path)
        prefix = os.path.splitext(md_basename)[0]
        assets_dir = os.path.join(md_dir, prefix + '.assets')

        if not os.path.isdir(assets_dir):
            self._log(f"未找到图片文件夹: {assets_dir}")
            self._log("没有图片可检查。")
            return

        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取MD文件失败: {e}")
            return

        referenced = self._extract_referenced_basenames(content)
        try:
            all_files = os.listdir(assets_dir)
        except Exception as e:
            self._log(f"无法访问图片文件夹: {e}")
            return

        image_files = [f for f in all_files if self._is_image_file(f)]
        unreferenced = [img for img in image_files if img not in referenced]

        if not unreferenced:
            self._log("所有图片均已被引用，没有未引用图片。")
        else:
            self._log(f"未引用的图片 ({len(unreferenced)} 个):")
            for img in unreferenced:
                self._log(f"  {img}")
            self.unreferenced_images = [os.path.join(assets_dir, img) for img in unreferenced]

    def _check_folder(self, folder):
        self._log(f"开始扫描文件夹: {folder}")
        md_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))

        if not md_files:
            self._log("未找到任何 .md 文件。")
            return

        self._log(f"共找到 {len(md_files)} 个 .md 文件\n")
        total_unreferenced = []

        for md_path in md_files:
            self._log(f"正在检查: {md_path}")
            md_dir = os.path.dirname(md_path)
            md_basename = os.path.basename(md_path)
            prefix = os.path.splitext(md_basename)[0]
            assets_dir = os.path.join(md_dir, prefix + '.assets')

            if not os.path.isdir(assets_dir):
                self._log(f"  未找到图片文件夹: {assets_dir}，跳过")
                continue

            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                self._log(f"  读取失败: {e}，跳过")
                continue

            referenced = self._extract_referenced_basenames(content)
            try:
                all_files = os.listdir(assets_dir)
            except Exception as e:
                self._log(f"  无法访问图片文件夹: {e}，跳过")
                continue

            image_files = [f for f in all_files if self._is_image_file(f)]
            unreferenced = [img for img in image_files if img not in referenced]

            if not unreferenced:
                self._log(f"  所有图片均已被引用")
            else:
                self._log(f"  未引用图片 ({len(unreferenced)} 个):")
                for img in unreferenced:
                    self._log(f"    {img}")
                for img in unreferenced:
                    total_unreferenced.append(os.path.join(assets_dir, img))

        self._log("\n===== 汇总结果 =====")
        if total_unreferenced:
            self._log(f"总计发现未引用图片 {len(total_unreferenced)} 个，可以进行移动或删除操作。")
        else:
            self._log("所有 .md 文件的图片均被引用，没有未引用图片。")
        self.unreferenced_images = total_unreferenced

    def move_images(self):
        if not self.unreferenced_images:
            if self.text_display.toPlainText().strip() == "":
                QMessageBox.warning(self, "提示", "请先执行“检查”操作")
            else:
                QMessageBox.information(self, "提示", "没有未引用的图片可移动")
            return

        dest = self.dest_edit.text().strip()
        if not dest:
            dest = r'C:\Users\Administrator\Downloads\md图未引用图片转移站'
            self._log(f"目标目录为空，将使用默认路径: {dest}")

        dest = os.path.abspath(dest)
        try:
            os.makedirs(dest, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建目标目录: {e}")
            return

        file_list = "\n".join(os.path.basename(p) for p in self.unreferenced_images)
        msg_box = QMessageBox(QMessageBox.Question, "确认移动",
                              f"以下 {len(self.unreferenced_images)} 个未引用图片将被移动到:\n{dest}\n\n确定继续吗？",
                              QMessageBox.Yes | QMessageBox.No, self)
        msg_box.setDetailedText(file_list)
        if msg_box.exec_() != QMessageBox.Yes:
            return

        self._log("\n开始移动...")
        success_count = 0
        for src in self.unreferenced_images:
            if not os.path.isfile(src):
                self._log(f"[跳过] 文件不存在: {src}")
                continue
            filename = os.path.basename(src)
            dst = os.path.join(dest, filename)
            try:
                if os.path.exists(dst):
                    base, ext = os.path.splitext(filename)
                    dst = os.path.join(dest, f"{base}_副本{ext}")
                shutil.move(src, dst)
                self._log(f"已移动: {filename} -> {dst}")
                success_count += 1
            except Exception as e:
                self._log(f"移动失败 {filename}: {e}")

        self._log(f"\n移动完成，共成功移动 {success_count}/{len(self.unreferenced_images)} 个文件。")
        self.unreferenced_images = []

    def delete_images(self):
        if not self.unreferenced_images:
            if self.text_display.toPlainText().strip() == "":
                QMessageBox.warning(self, "提示", "请先执行“检查”操作")
            else:
                QMessageBox.information(self, "提示", "没有未引用的图片可删除")
            return

        file_list = "\n".join(os.path.basename(p) for p in self.unreferenced_images)
        msg_box = QMessageBox(QMessageBox.Question, "确认删除 - 第一步",
                              "以下图片将被删除，确定继续吗？",
                              QMessageBox.Yes | QMessageBox.No, self)
        msg_box.setDetailedText(file_list)
        if msg_box.exec_() != QMessageBox.Yes:
            return

        reply = QMessageBox.question(self, "确认删除 - 第二步",
                                     "您确定删除所有未引用的图片吗？此操作不可恢复！",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self._log("\n开始删除...")
        deleted_count = 0
        for src in self.unreferenced_images:
            if not os.path.isfile(src):
                self._log(f"[跳过] 文件不存在: {src}")
                continue
            try:
                os.remove(src)
                self._log(f"已删除: {os.path.basename(src)}")
                deleted_count += 1
            except Exception as e:
                self._log(f"删除失败 {os.path.basename(src)}: {e}")

        self._log(f"\n删除完成，共成功删除 {deleted_count}/{len(self.unreferenced_images)} 个文件。")
        self.unreferenced_images = []


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
        self.start_minimized = "--minimized" in sys.argv
        self._force_quit = False

        self.tray_watchdog = QTimer()
        self.tray_watchdog.timeout.connect(self.ensure_tray_visible)
        self.tray_watchdog.setInterval(2000)

        self.setWindowIcon(QIcon(self.get_logo_path()))
        self.init_tray_icon()
        self.init_ui()

        self.tray_watchdog.start()

        if self.start_minimized:
            QTimer.singleShot(100, self.hide_to_tray)
        else:
            self.show()
            self.raise_()
            self.activateWindow()

        QTimer.singleShot(100, self.load_notes)

    def get_logo_path(self):
        logo_paths = ["logo.ico", os.path.join(os.path.dirname(__file__), "logo.ico"), get_resource_path("logo.ico")]
        for path in logo_paths:
            if os.path.exists(path):
                return path
        return None

    def init_tray_icon(self):
        try:
            if self.tray_icon:
                try:
                    self.tray_icon.hide()
                    self.tray_icon.deleteLater()
                except:
                    pass
            self.tray_icon = QSystemTrayIcon(self)
            icon_path = self.get_logo_path()
            if icon_path:
                icon = QIcon(icon_path)
                if icon.isNull():
                    icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
                self.tray_icon.setIcon(icon)
            else:
                self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

            tray_menu = QMenu()
            show_action = tray_menu.addAction("显示主窗口")
            show_action.triggered.connect(self.show_from_tray)
            tray_menu.addSeparator()
            quit_action = tray_menu.addAction("退出")
            quit_action.triggered.connect(self.quit_application)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)

            self.tray_icon.show()
            self.tray_icon.setParent(self)
        except Exception as e:
            print(f"初始化托盘图标错误: {e}")
            self.tray_icon = None

    def ensure_tray_visible(self):
        if self.tray_icon is None:
            self.init_tray_icon()
            return
        if not self.tray_icon.isVisible():
            if QSystemTrayIcon.isSystemTrayAvailable():
                try:
                    self.tray_icon.show()
                except Exception as e:
                    self.init_tray_icon()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()

    def show_from_tray(self):
        try:
            if self.isVisible():
                self.activateWindow()
                self.raise_()
                return
            self.showNormal()
            self.activateWindow()
            self.raise_()
            self.is_minimized_to_tray = False
            self.statusBar().showMessage("已从托盘恢复")
        except Exception as e:
            print(f"从托盘恢复错误: {e}")

    def hide_to_tray(self):
        try:
            if not self.tray_icon:
                self.init_tray_icon()
            self.hide()
            self.is_minimized_to_tray = True
            if self.tray_icon:
                if not self.tray_icon.isVisible():
                    if QSystemTrayIcon.isSystemTrayAvailable():
                        self.tray_icon.show()
                self.tray_icon.show()
        except Exception as e:
            print(f"隐藏到托盘错误: {e}")

    def quit_application(self):
        if hasattr(self, '_quitting') and self._quitting:
            return
        self._quitting = True
        self._force_quit = True

        try:
            self.config.data["window_geometry"] = self.saveGeometry().toHex().data().decode()
            self.config.save_config()
        except:
            pass

        if self.scanner and self.scanner.isRunning():
            self.scanner.cancel()
            self.scanner.wait(500)

        if self.tray_watchdog:
            self.tray_watchdog.stop()

        if self.tray_icon:
            try:
                self.tray_icon.hide()
                self.tray_icon.deleteLater()
            except:
                pass
            self.tray_icon = None

        self.close()
        QApplication.quit()
        os._exit(0)

    def init_ui(self):
        try:
            self.setWindowTitle("森明笔记 msm_bcf_works@163.com")
            self.setGeometry(100, 100, 1200, 800)
            if self.config.data.get("window_geometry"):
                try:
                    self.restoreGeometry(QByteArray.fromHex(self.config.data["window_geometry"].encode()))
                except:
                    pass

            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout()
            main_layout.setContentsMargins(10, 10, 10, 10)

            toolbar = QHBoxLayout()
            self.search_edit = QLineEdit()
            self.search_edit.setPlaceholderText("搜索笔记...")
            self.search_edit.textChanged.connect(self.filter_notes)
            toolbar.addWidget(self.search_edit)

            self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
            self.search_shortcut.activated.connect(self.focus_search)

            settings_btn = QPushButton("⚙ 设置")
            settings_btn.clicked.connect(self.open_settings)
            toolbar.addWidget(settings_btn)

            toolbar.addWidget(QLabel("排序:"))
            self.sort_combo = QComboBox()
            self.sort_combo.addItems(["名称 ↑", "名称 ↓", "修改时间 ↑", "修改时间 ↓",
                                      "创建时间 ↑", "创建时间 ↓", "大小 ↑", "大小 ↓", "类型 ↑", "类型 ↓"])
            sort_map = {"name_asc":0, "name_desc":1, "mod_asc":2, "mod_desc":3,
                        "create_asc":4, "create_desc":5, "size_asc":6, "size_desc":7,
                        "type_asc":8, "type_desc":9}
            self.sort_combo.setCurrentIndex(sort_map.get(self.current_sort, 0))
            self.sort_combo.currentIndexChanged.connect(self.change_sort)
            toolbar.addWidget(self.sort_combo)

            self.view_toggle_btn = QPushButton()
            self.update_view_button()
            self.view_toggle_btn.clicked.connect(self.toggle_view)
            toolbar.addWidget(self.view_toggle_btn)

            self.theme_toggle_btn = QPushButton(f"主题: {self.current_theme}")
            self.theme_toggle_btn.clicked.connect(self.toggle_theme)
            toolbar.addWidget(self.theme_toggle_btn)

            self.refresh_btn = QPushButton("🔄 刷新")
            self.refresh_btn.clicked.connect(self.refresh_notes)
            toolbar.addWidget(self.refresh_btn)

            self.add_btn = QPushButton("新增")
            self.add_btn.clicked.connect(self.show_add_note_menu)
            toolbar.addWidget(self.add_btn)

            self.md_redundant_btn = QPushButton("MD冗余")
            self.md_redundant_btn.clicked.connect(self.open_md_redundant)
            toolbar.addWidget(self.md_redundant_btn)

            toolbar.addStretch()
            main_layout.addLayout(toolbar)

            self.view_container = QStackedWidget()
            self.list_widget = QWidget()
            list_layout = QVBoxLayout(self.list_widget)
            list_layout.setContentsMargins(0,0,0,0)
            self.notes_list = QListWidget()
            self.notes_list.setUniformItemSizes(False)
            self.notes_list.itemDoubleClicked.connect(self.open_note_from_list)
            self.notes_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.notes_list.customContextMenuRequested.connect(self.show_list_context_menu)
            list_layout.addWidget(self.notes_list)

            self.grid_widget = QWidget()
            grid_layout = QVBoxLayout(self.grid_widget)
            grid_layout.setContentsMargins(0,0,0,0)
            self.grid_scroll_area = QScrollArea()
            self.grid_scroll_area.setWidgetResizable(True)
            self.grid_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.grid_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.grid_scroll_area.setFrameShape(QFrame.NoFrame)
            self.grid_container = QWidget()
            self.grid_scroll_area.setWidget(self.grid_container)
            self.grid_layout = QGridLayout(self.grid_container)
            self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            self.grid_layout.setContentsMargins(5, 5, 5, 5)
            self.grid_layout.setHorizontalSpacing(5)
            self.grid_layout.setVerticalSpacing(5)
            grid_layout.addWidget(self.grid_scroll_area)

            self.view_container.addWidget(self.list_widget)
            self.view_container.addWidget(self.grid_widget)
            self.view_container.setCurrentIndex(0 if self.current_view == "list" else 1)

            main_layout.addWidget(self.view_container, 1)
            self.progress_label = QLabel("就绪")
            self.progress_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(self.progress_label)

            central_widget.setLayout(main_layout)
            self.statusBar().showMessage("就绪")
            self.apply_theme(self.current_theme)

            if self.current_view == "grid":
                QTimer.singleShot(200, self.force_refresh_grid)
        except Exception as e:
            print(f"初始化UI错误: {e}")
            traceback.print_exc()

    def open_md_redundant(self):
        dialog = MDRedundantDialog(self.config, self)
        dialog.exec_()

    def focus_search(self):
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def show_add_note_menu(self):
        menu = QMenu()
        if self.current_theme == "dark":
            menu.setStyleSheet("QMenu{background:#3c3c3c;color:white;border:1px solid #555} QMenu::item{padding:5px 20px} QMenu::item:selected{background:#4c4c4c}")
        else:
            menu.setStyleSheet("QMenu{background:white;color:black;border:1px solid #ccc} QMenu::item{padding:5px 20px} QMenu::item:selected{background:#f0f0f0}")
        action_md = menu.addAction("md笔记")
        action_md_folder = menu.addAction("md文件夹笔记")
        action_txt = menu.addAction("txt笔记")
        pos = self.add_btn.mapToGlobal(QPoint(0, self.add_btn.height()))
        action = menu.exec_(pos)
        if action == action_md:
            self.add_simple_note("md")
        elif action == action_md_folder:
            self.add_folder_note()
        elif action == action_txt:
            self.add_simple_note("txt")

    def add_simple_note(self, ext):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"创建{ext.upper()}笔记")
        dialog.setFixedSize(400, 150)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        name_edit = QLineEdit()
        form.addRow("笔记名称:", name_edit)
        layout.addLayout(form)
        btn_box = QHBoxLayout()
        btn_create = QPushButton("创建笔记")
        btn_cancel = QPushButton("取消")
        btn_box.addStretch()
        btn_box.addWidget(btn_create)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

        btn_cancel.clicked.connect(dialog.reject)
        def on_create():
            note_name = name_edit.text().strip()
            if not note_name:
                QMessageBox.warning(dialog, "输入错误", "笔记名称不能为空")
                return
            valid, err = validate_windows_name(note_name, is_folder=False)
            if not valid:
                QMessageBox.warning(dialog, "非法名称", err)
                return
            base_dir = self.config.data["notes_folder"]
            if not os.path.exists(base_dir):
                try:
                    os.makedirs(base_dir, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(dialog, "错误", f"无法创建笔记文件夹:\n{str(e)}")
                    return
            file_path = os.path.join(base_dir, f"{note_name}.{ext}")
            if os.path.exists(file_path):
                QMessageBox.warning(dialog, "文件已存在", f"文件 {file_path} 已存在，请更换名称")
                return
            confirm = QMessageBox.question(
                dialog, "确认创建",
                f"是否创建 {file_path}？",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        pass
                    dialog.accept()
                except Exception as e:
                    QMessageBox.critical(dialog, "创建失败", f"无法创建文件:\n{str(e)}")
        btn_create.clicked.connect(on_create)
        if dialog.exec_() == QDialog.Accepted:
            self.statusBar().showMessage("笔记创建成功")
            self.refresh_notes()

    def add_folder_note(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("创建MD文件夹笔记")
        dialog.setFixedSize(450, 220)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        folder_edit = QLineEdit()
        folder_edit.setPlaceholderText("可选，留空则使用笔记名称")
        note_edit = QLineEdit()
        note_edit.setPlaceholderText("必填，将作为md文件名")
        form.addRow("文件夹名:", folder_edit)
        form.addRow("笔记名称:", note_edit)
        layout.addLayout(form)
        btn_box = QHBoxLayout()
        btn_create = QPushButton("创建笔记")
        btn_cancel = QPushButton("取消")
        btn_box.addStretch()
        btn_box.addWidget(btn_create)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

        btn_cancel.clicked.connect(dialog.reject)
        def on_create():
            folder_name = folder_edit.text().strip()
            note_name = note_edit.text().strip()
            if not note_name:
                QMessageBox.warning(dialog, "输入错误", "笔记名称不能为空")
                return
            valid, err = validate_windows_name(note_name, is_folder=False)
            if not valid:
                QMessageBox.warning(dialog, "非法笔记名称", err)
                return
            if folder_name:
                valid, err = validate_windows_name(folder_name, is_folder=True)
                if not valid:
                    QMessageBox.warning(dialog, "非法文件夹名", err)
                    return
            else:
                folder_name = note_name
            base_dir = self.config.data["notes_folder"]
            if not os.path.exists(base_dir):
                try:
                    os.makedirs(base_dir, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(dialog, "错误", f"无法创建笔记文件夹:\n{str(e)}")
                    return
            target_folder = os.path.join(base_dir, folder_name)
            target_file = os.path.join(target_folder, f"{note_name}.md")
            if os.path.exists(target_folder):
                if not os.path.isdir(target_folder):
                    QMessageBox.warning(dialog, "路径冲突", f"已存在同名文件 {target_folder}，无法创建文件夹")
                    return
            if os.path.exists(target_file):
                QMessageBox.warning(dialog, "文件已存在", f"文件 {target_file} 已存在，请更换名称")
                return
            confirm = QMessageBox.question(
                dialog, "确认创建",
                f"是否创建文件夹:\n{target_folder}\n并在其中创建文件:\n{target_file}？",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                try:
                    os.makedirs(target_folder, exist_ok=True)
                    with open(target_file, 'w', encoding='utf-8') as f:
                        pass
                    dialog.accept()
                except Exception as e:
                    QMessageBox.critical(dialog, "创建失败", f"无法创建文件夹或文件:\n{str(e)}")
        btn_create.clicked.connect(on_create)
        if dialog.exec_() == QDialog.Accepted:
            self.statusBar().showMessage("文件夹笔记创建成功")
            self.refresh_notes()

    def force_refresh_grid(self):
        if self.current_view == "grid":
            notes = self.filtered_notes if self.filtered_notes else self.current_notes
            if notes:
                self.refresh_grid_view(notes)

    def update_view_button(self):
        self.view_toggle_btn.setText("网格视图" if self.current_view == "list" else "列表视图")

    def toggle_view(self):
        try:
            self.current_view = "grid" if self.current_view == "list" else "list"
            self.config.data["view_mode"] = self.current_view
            self.config.save_config()
            self.update_view_button()
            self.view_container.setCurrentIndex(0 if self.current_view == "list" else 1)
            notes = self.filtered_notes if self.filtered_notes else self.current_notes
            self.display_notes(notes)
            if self.current_view == "grid":
                QTimer.singleShot(100, self.force_refresh_grid)
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
        self.current_notes = []
        self.filtered_notes = []
        self.load_notes()

    def apply_theme(self, theme):
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2b2b2b; color: #ffffff; }
                QLineEdit, QComboBox { background-color: #3c3c3c; border:1px solid #555; padding:5px; }
                QPushButton { background-color: #3c3c3c; border:1px solid #555; padding:5px 10px; }
                QPushButton:hover { background-color: #4c4c4c; }
                QListWidget { background-color: transparent; border:1px solid #555; }
                QScrollArea { background-color: transparent; border:none; }
                QLabel { color:#ffffff; }
            """)
            self.progress_label.setStyleSheet("color:#ffffff;")
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #f5f5f5; color: #000000; }
                QLineEdit, QComboBox { background-color: #ffffff; border:1px solid #ccc; padding:5px; }
                QPushButton { background-color: #ffffff; border:1px solid #ccc; padding:5px 10px; }
                QPushButton:hover { background-color: #f0f0f0; }
                QListWidget { background-color: #ffffff; border:1px solid #ccc; }
                QScrollArea { background-color: #f5f5f5; border:none; }
                QLabel { color:#000000; }
            """)
            self.progress_label.setStyleSheet("color:#000000;")

    def load_notes(self):
        try:
            notes_folder = self.config.data["notes_folder"]
            if not os.path.exists(notes_folder):
                QMessageBox.warning(self, "警告", f"笔记文件夹不存在:\n{notes_folder}")
                return
            if self.scanner and self.scanner.isRunning():
                self.scanner.cancel()
                self.scanner.wait()
            self.scanner = FileSystemScanner(notes_folder, self.config)
            self.scanner.scan_progress.connect(self.update_progress)
            self.scanner.scan_complete.connect(self.on_scan_complete)
            self.scanner.start()
            self.statusBar().showMessage("正在扫描笔记...")
        except Exception as e:
            print(f"加载笔记错误: {e}")

    def update_progress(self, current, total, filename):
        self.progress_label.setText(f"扫描中... {current}/{total}: {filename[:30]}")

    def on_scan_complete(self, notes):
        self.current_notes = notes
        self.filter_notes()
        self.statusBar().showMessage(f"找到 {len(notes)} 个笔记")
        self.progress_label.setText(f"找到 {len(notes)} 个笔记")
        if self.current_view == "grid":
            QTimer.singleShot(50, self.force_refresh_grid)

    def filter_notes(self):
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

    def sort_notes(self, notes):
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

    def display_notes(self, notes):
        if self.current_view == "list":
            self.refresh_list_view(notes)
        else:
            self.refresh_grid_view(notes)

    def refresh_list_view(self, notes):
        try:
            self.notes_list.clear()
            if not notes:
                return
            pinned = [n for n in notes if n.get("is_pinned", False)]
            unpinned = [n for n in notes if not n.get("is_pinned", False)]
            sorted_notes = self.sort_notes(pinned) + self.sort_notes(unpinned)
            for note in sorted_notes:
                widget = CustomListWidgetItem(note, self.current_theme)
                item = QListWidgetItem(self.notes_list)
                item.setSizeHint(widget.sizeHint())
                item.setData(Qt.UserRole, note)
                self.notes_list.addItem(item)
                self.notes_list.setItemWidget(item, widget)
                widget.list_item = item
        except Exception as e:
            print(f"刷新列表视图错误: {e}")

    def refresh_grid_view(self, notes):
        try:
            for i in reversed(range(self.grid_layout.count())):
                item = self.grid_layout.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()

            if not notes:
                return

            pinned = [n for n in notes if n.get("is_pinned", False)]
            unpinned = [n for n in notes if not n.get("is_pinned", False)]
            sorted_notes = self.sort_notes(pinned) + self.sort_notes(unpinned)

            viewport = self.grid_scroll_area.viewport()
            available_width = viewport.width() - self.grid_layout.contentsMargins().left() - self.grid_layout.contentsMargins().right()
            if available_width <= 0:
                available_width = self.width() - 50
            if available_width <= 0:
                available_width = 800

            item_width = 160
            spacing = self.grid_layout.horizontalSpacing()
            items_per_row = max(1, (available_width + spacing) // (item_width + spacing))

            for i in reversed(range(self.grid_layout.columnCount())):
                self.grid_layout.setColumnStretch(i, 0)
            for col in range(items_per_row):
                self.grid_layout.setColumnStretch(col, 1)

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
        if isinstance(item, QListWidgetItem):
            note_info = item.data(Qt.UserRole)
            if note_info:
                self.open_note_internal(note_info)

    def open_note_from_grid(self, note_info):
        self.open_note_internal(note_info)

    def open_note_internal(self, note_info):
        try:
            file_path = note_info["path"]
            file_type = note_info["type"]
            file_type_info = self.config.get_file_type_info(file_type)
            if not file_type_info:
                QMessageBox.warning(self, "文件类型不支持", f"文件类型 '{file_type}' 不受支持。请在设置中添加。")
                return
            external_tool = file_type_info.get("external", "")
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "错误", f"文件不存在:\n{file_path}")
                return
            if not external_tool:
                QMessageBox.warning(self, "未配置打开方式", f"文件类型 '{file_type}' 没有配置默认打开方式。请在设置中添加。")
                return
            self.open_with_external(file_path, external_tool)
        except Exception as e:
            print(f"打开笔记错误: {e}")

    def open_with_external(self, file_path, external_tool):
        try:
            if sys.platform == "win32":
                if external_tool and os.path.exists(external_tool):
                    subprocess.Popen([external_tool, file_path], shell=True)
                else:
                    try:
                        os.startfile(file_path)
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
            self.statusBar().showMessage("打开文件")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件:\n{str(e)}")

    def show_list_context_menu(self, position):
        item = self.notes_list.itemAt(position)
        if item:
            note_info = item.data(Qt.UserRole)
            if note_info:
                self.show_context_menu(note_info, self.notes_list.mapToGlobal(position))

    def show_grid_context_menu(self, note_info, position):
        self.show_context_menu(note_info, position)

    def show_context_menu(self, note_info, position):
        menu = QMenu()
        if self.current_theme == "dark":
            menu.setStyleSheet("QMenu{background:#3c3c3c;color:white;border:1px solid #555} QMenu::item{padding:5px 20px} QMenu::item:selected{background:#4c4c4c}")
        else:
            menu.setStyleSheet("QMenu{background:white;color:black;border:1px solid #ccc} QMenu::item{padding:5px 20px} QMenu::item:selected{background:#f0f0f0}")
        open_action = menu.addAction("打开")
        show_in_explorer = menu.addAction("在文件资源管理器中显示")
        copy_path_action = menu.addAction("复制完整路径")
        rename_action = menu.addAction("重命名")
        if note_info.get("is_pinned", False):
            pin_action = menu.addAction("取消置顶")
        else:
            pin_action = menu.addAction("置顶")
        action = menu.exec_(position)
        if action == open_action:
            self.open_note_internal(note_info)
        elif action == show_in_explorer:
            self.show_in_explorer(note_info)
        elif action == copy_path_action:
            self.copy_full_path(note_info)
        elif action == rename_action:
            self.rename_note(note_info)
        elif action == pin_action:
            self.toggle_pin_status(note_info)

    def rename_note(self, note_info):
        is_folder = note_info.get("is_folder", False)
        old_folder_path = note_info.get("folder_path", "")
        old_file_path = note_info["path"]
        old_file_basename = os.path.basename(old_file_path)
        old_file_name_no_ext, old_ext = os.path.splitext(old_file_basename)
        old_ext = old_ext.lstrip('.')

        dialog = QDialog(self)
        dialog.setWindowTitle("重命名笔记")
        layout = QVBoxLayout(dialog)

        if is_folder:
            form = QFormLayout()
            folder_edit = QLineEdit()
            folder_edit.setText(os.path.basename(old_folder_path))
            folder_edit.setPlaceholderText("文件夹名（留空则自动使用笔记名）")
            form.addRow("文件夹名:", folder_edit)
            file_edit = QLineEdit()
            file_edit.setText(old_file_name_no_ext)
            form.addRow("笔记文件名:", file_edit)
            layout.addLayout(form)
        else:
            file_edit = QLineEdit()
            file_edit.setText(old_file_name_no_ext)
            layout.addWidget(QLabel("新文件名:"))
            layout.addWidget(file_edit)

        btn_box = QHBoxLayout()
        btn_update = QPushButton("更新笔记名字")
        btn_cancel = QPushButton("取消")
        btn_box.addStretch()
        btn_box.addWidget(btn_update)
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

        dialog.setMinimumWidth(400)

        def on_update():
            new_file_name = file_edit.text().strip()
            if not new_file_name:
                QMessageBox.warning(dialog, "输入错误", "笔记文件名不能为空")
                return
            valid, err = validate_windows_name(new_file_name, is_folder=False)
            if not valid:
                QMessageBox.warning(dialog, "非法笔记文件名", err)
                return

            new_folder_name = None
            if is_folder:
                folder_name = folder_edit.text().strip()
                if folder_name:
                    valid, err = validate_windows_name(folder_name, is_folder=True)
                    if not valid:
                        QMessageBox.warning(dialog, "非法文件夹名", err)
                        return
                    new_folder_name = folder_name
                else:
                    new_folder_name = new_file_name

            old_folder_abs = os.path.abspath(old_folder_path)
            old_file_abs = os.path.abspath(old_file_path)
            base_dir = os.path.dirname(old_folder_abs) if is_folder else os.path.dirname(old_file_abs)

            file_name_changed = (new_file_name != old_file_name_no_ext)
            folder_name_changed = (is_folder and new_folder_name != os.path.basename(old_folder_abs))

            if not file_name_changed and not folder_name_changed:
                QMessageBox.information(dialog, "提示", "名称未发生变化，无需重命名")
                return

            # 构建新路径（在旧文件夹内）
            if is_folder:
                new_file_path_in_old_folder = os.path.join(old_folder_abs, f"{new_file_name}.{old_ext}")
                new_assets_in_old_folder = os.path.join(old_folder_abs, f"{new_file_name}.assets")
                old_assets = os.path.join(old_folder_abs, f"{old_file_name_no_ext}.assets")
            else:
                new_file_path = os.path.join(base_dir, f"{new_file_name}.{old_ext}")
                if os.path.exists(new_file_path):
                    QMessageBox.warning(dialog, "错误", f"目标文件已存在: {new_file_path}")
                    return

            # 确认对话框
            if is_folder:
                old_show = f"文件夹 '{os.path.basename(old_folder_abs)}' 和文件 '{old_file_basename}'"
                new_folder_display = new_folder_name if folder_name_changed else os.path.basename(old_folder_abs)
                new_show = f"文件夹 '{new_folder_display}' 和文件 '{new_file_name}.{old_ext}'"
            else:
                old_show = f"文件 '{old_file_basename}'"
                new_show = f"文件 '{new_file_name}.{old_ext}'"

            confirm = QMessageBox.question(
                dialog, "确认重命名",
                f"是否将 {old_show} 重命名为 {new_show} ？",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm != QMessageBox.Yes:
                return

            try:
                if is_folder:
                    # 1. 重命名 .md 文件（在旧文件夹内）
                    if file_name_changed:
                        if os.path.exists(new_file_path_in_old_folder):
                            QMessageBox.warning(dialog, "错误", f"目标文件已存在: {new_file_path_in_old_folder}")
                            return
                        os.rename(old_file_abs, new_file_path_in_old_folder)
                        current_file_path = new_file_path_in_old_folder
                    else:
                        current_file_path = old_file_abs

                    # 2. 重命名 .assets 文件夹（如果文件名变了）
                    if file_name_changed and os.path.exists(old_assets):
                        if os.path.exists(new_assets_in_old_folder):
                            QMessageBox.warning(dialog, "错误", f"目标 .assets 文件夹已存在: {new_assets_in_old_folder}")
                            # 回退文件重命名
                            os.rename(current_file_path, old_file_abs)
                            return
                        os.rename(old_assets, new_assets_in_old_folder)

                    # 3. 更新文件内容中的图片引用（只替换 .assets/ 前的文件名，不转义）
                    if file_name_changed:
                        try:
                            with open(current_file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            # 旧模式需要转义，新模式直接拼接
                            old_pattern = re.escape(old_file_name_no_ext) + r'\.assets/'
                            new_pattern = new_file_name + '.assets/'
                            new_content = re.sub(old_pattern, new_pattern, content)
                            if new_content != content:
                                with open(current_file_path, 'w', encoding='utf-8') as f:
                                    f.write(new_content)
                        except Exception as e:
                            print(f"更新文件内容失败: {e}")

                    # 4. 重命名外层文件夹（如果文件夹名变了）
                    if folder_name_changed:
                        new_folder_abs = os.path.join(base_dir, new_folder_name)
                        if os.path.exists(new_folder_abs):
                            # 回退之前的修改
                            if file_name_changed:
                                os.rename(current_file_path, old_file_abs)
                                if os.path.exists(new_assets_in_old_folder):
                                    os.rename(new_assets_in_old_folder, old_assets)
                            QMessageBox.warning(dialog, "错误", f"目标文件夹已存在: {new_folder_abs}")
                            return
                        os.rename(old_folder_abs, new_folder_abs)
                        note_info["folder_path"] = new_folder_abs
                        note_info["path"] = os.path.join(new_folder_abs, f"{new_file_name}.{old_ext}")
                        note_info["name"] = new_folder_name
                    else:
                        note_info["folder_path"] = old_folder_abs
                        note_info["path"] = current_file_path
                        if file_name_changed:
                            note_info["name"] = os.path.basename(old_folder_abs)
                        else:
                            note_info["name"] = os.path.basename(old_folder_abs)
                else:
                    # 纯文件重命名
                    new_file_path = os.path.join(base_dir, f"{new_file_name}.{old_ext}")
                    if os.path.exists(new_file_path):
                        QMessageBox.warning(dialog, "错误", f"目标文件已存在: {new_file_path}")
                        return
                    os.rename(old_file_abs, new_file_path)
                    note_info["path"] = new_file_path
                    note_info["name"] = f"{new_file_name}.{old_ext}"

                # 更新置顶状态
                old_pinned_path = old_file_abs
                new_file_abs = note_info["path"]
                if self.config.is_note_pinned(old_pinned_path):
                    self.config.unpin_note(old_pinned_path)
                    self.config.pin_note(new_file_abs)
                    note_info["is_pinned"] = True

                self.update_all_notes_pinned_status()
                self.display_notes(self.filtered_notes if self.filtered_notes else self.current_notes)
                self.statusBar().showMessage("重命名成功")
                dialog.accept()
                self.refresh_notes()
            except Exception as e:
                QMessageBox.critical(dialog, "重命名失败", f"重命名时发生错误:\n{str(e)}")

        btn_update.clicked.connect(on_update)
        btn_cancel.clicked.connect(dialog.reject)

        dialog.exec_()

    def copy_full_path(self, note_info):
        try:
            path = note_info.get("path", "")
            if path and os.path.exists(path):
                QApplication.clipboard().setText(path)
                self.statusBar().showMessage(f"已复制路径: {path}")
            else:
                QMessageBox.warning(self, "错误", "无法复制路径: 文件不存在")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"复制路径失败: {e}")

    def toggle_pin_status(self, note_info):
        file_path = note_info["path"]
        if note_info.get("is_pinned", False):
            if self.config.unpin_note(file_path):
                note_info["is_pinned"] = False
                self.update_all_notes_pinned_status()
                self.display_notes(self.filtered_notes if self.filtered_notes else self.current_notes)
                self.statusBar().showMessage(f"已取消置顶: {note_info['name']}")
            else:
                QMessageBox.warning(self, "错误", "取消置顶失败")
        else:
            if self.config.pin_note(file_path):
                note_info["is_pinned"] = True
                self.update_all_notes_pinned_status()
                self.display_notes(self.filtered_notes if self.filtered_notes else self.current_notes)
                self.statusBar().showMessage(f"已置顶: {note_info['name']}")
            else:
                QMessageBox.warning(self, "错误", "置顶失败")

    def update_all_notes_pinned_status(self):
        for note in self.current_notes:
            note["is_pinned"] = self.config.is_note_pinned(note["path"])
        for note in self.filtered_notes:
            note["is_pinned"] = self.config.is_note_pinned(note["path"])

    def show_in_explorer(self, note_info):
        try:
            file_path = note_info["path"]
            if sys.platform == "win32":
                abs_path = os.path.abspath(file_path)
                try:
                    subprocess.run(f'explorer /select, "{abs_path}"', shell=True)
                except:
                    folder = os.path.dirname(abs_path)
                    os.startfile(folder)
            else:
                folder = os.path.dirname(file_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法在资源管理器中显示:\n{str(e)}")

    def change_sort(self, index):
        sort_map = ["name_asc","name_desc","mod_asc","mod_desc","create_asc","create_desc","size_asc","size_desc","type_asc","type_desc"]
        if index < len(sort_map):
            self.current_sort = sort_map[index]
            self.config.data["sort_by"] = self.current_sort
            self.config.save_config()
            notes = self.filtered_notes if self.filtered_notes else self.current_notes
            self.display_notes(notes)

    def open_settings(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QCheckBox

        class SettingsDialog(QDialog):
            def __init__(self, config, theme):
                super().__init__()
                self.config = config
                self.theme = theme
                self.init_ui()
                self.apply_theme(theme)

            def init_ui(self):
                self.setWindowTitle("设置 - 森明笔记")
                self.resize(700, 600)
                layout = QVBoxLayout()

                folder_group = QGroupBox("笔记文件夹设置")
                folder_layout = QVBoxLayout()
                hbox = QHBoxLayout()
                self.folder_edit = QLineEdit(self.config.data["notes_folder"])
                browse_btn = QPushButton("浏览...")
                browse_btn.clicked.connect(self.browse_folder)
                hbox.addWidget(QLabel("笔记总文件夹:"))
                hbox.addWidget(self.folder_edit, 1)
                hbox.addWidget(browse_btn)
                folder_layout.addLayout(hbox)
                folder_group.setLayout(folder_layout)

                behavior_group = QGroupBox("程序行为设置")
                behavior_layout = QHBoxLayout()
                self.auto_start_cb = QCheckBox("开机自启动")
                self.auto_start_cb.setChecked(self.config.data.get("auto_start", False))
                behavior_layout.addWidget(self.auto_start_cb)
                behavior_layout.addSpacing(20)
                behavior_layout.addWidget(QLabel("关闭窗口按钮行为:"))
                self.close_action_combo = QComboBox()
                self.close_action_combo.addItems(["隐藏到托盘", "直接退出程序"])
                close_action = self.config.data.get("close_action", "hide_to_tray")
                self.close_action_combo.setCurrentIndex(0 if close_action == "hide_to_tray" else 1)
                behavior_layout.addWidget(self.close_action_combo)
                behavior_layout.addStretch()
                behavior_group.setLayout(behavior_layout)

                type_group = QGroupBox("文件类型设置")
                type_layout = QVBoxLayout()
                self.type_table = QTableWidget()
                self.type_table.setColumnCount(3)
                self.type_table.setHorizontalHeaderLabels(["扩展名", "图标", "外部工具路径"])
                self.type_table.setAlternatingRowColors(True)
                self.type_table.horizontalHeader().setStretchLastSection(True)
                self.type_table.setSelectionBehavior(QTableWidget.SelectRows)
                self.load_file_types()
                btn_layout = QHBoxLayout()
                add_btn = QPushButton("添加")
                add_btn.clicked.connect(self.add_file_type)
                remove_btn = QPushButton("删除")
                remove_btn.clicked.connect(self.remove_file_type)
                btn_layout.addWidget(add_btn)
                btn_layout.addWidget(remove_btn)
                btn_layout.addStretch()
                type_layout.addWidget(self.type_table, 1)
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
                layout.addWidget(behavior_group)
                layout.addWidget(type_group, 1)
                layout.addLayout(button_layout)
                self.setLayout(layout)

            def apply_theme(self, theme):
                if theme == "dark":
                    self.setStyleSheet("""
                        QDialog,QGroupBox,QTableWidget { background-color:#2b2b2b; color:#fff; }
                        QLineEdit,QComboBox,QCheckBox { background-color:#3c3c3c; color:#fff; border:1px solid #555; }
                        QPushButton { background-color:#3c3c3c; border:1px solid #555; padding:5px; }
                        QPushButton:hover { background-color:#4c4c4c; }
                        QHeaderView::section { background-color:#3c3c3c; color:white; }
                    """)
                else:
                    self.setStyleSheet("""
                        QDialog,QGroupBox,QTableWidget { background-color:#f5f5f5; color:#000; }
                        QLineEdit,QComboBox,QCheckBox { background-color:#fff; border:1px solid #ccc; }
                        QPushButton { background-color:#fff; border:1px solid #ccc; padding:5px; }
                        QPushButton:hover { background-color:#f0f0f0; }
                        QHeaderView::section { background-color:#fff; color:black; }
                    """)

            def browse_folder(self):
                folder = QFileDialog.getExistingDirectory(self, "选择笔记文件夹", self.folder_edit.text())
                if folder:
                    self.folder_edit.setText(folder)

            def load_file_types(self):
                self.type_table.setRowCount(len(self.config.data["file_types"]))
                for i, (type_str, info) in enumerate(self.config.data["file_types"].items()):
                    self.type_table.setItem(i, 0, QTableWidgetItem(type_str))
                    self.type_table.setItem(i, 1, QTableWidgetItem(info.get("icon", "txt.png")))
                    self.type_table.setItem(i, 2, QTableWidgetItem(info.get("external", "")))

            def add_file_type(self):
                row = self.type_table.rowCount()
                self.type_table.insertRow(row)
                self.type_table.setItem(row, 0, QTableWidgetItem("新扩展名"))
                self.type_table.setItem(row, 1, QTableWidgetItem("txt.png"))
                self.type_table.setItem(row, 2, QTableWidgetItem(""))

            def remove_file_type(self):
                row = self.type_table.currentRow()
                if row >= 0:
                    self.type_table.removeRow(row)

            def save_all(self):
                self.config.data["notes_folder"] = self.folder_edit.text()
                self.config.data["auto_start"] = self.auto_start_cb.isChecked()
                self.config.data["close_action"] = "hide_to_tray" if self.close_action_combo.currentIndex() == 0 else "quit"
                new_file_types = {}
                for row in range(self.type_table.rowCount()):
                    type_str = self.type_table.item(row, 0).text().strip()
                    if not type_str:
                        continue
                    icon = self.type_table.item(row, 1).text().strip()
                    external = self.type_table.item(row, 2).text().strip()
                    new_file_types[type_str] = {"icon": icon, "external": external}
                self.config.data["file_types"] = new_file_types
                if self.config.save_config():
                    QMessageBox.information(self, "成功", "设置已保存！")
                    self.accept()
                else:
                    QMessageBox.warning(self, "错误", "保存设置失败！")

        dialog = SettingsDialog(self.config, self.current_theme)
        if dialog.exec_() == QDialog.Accepted:
            self.current_notes = []
            self.filtered_notes = []
            self.load_notes()

    def closeEvent(self, event):
        if self._force_quit:
            event.accept()
            return

        try:
            self.config.data["window_geometry"] = self.saveGeometry().toHex().data().decode()
            self.config.save_config()

            if self.scanner and self.scanner.isRunning():
                self.scanner.cancel()
                self.scanner.wait()

            if self.config.data.get("close_action") == "hide_to_tray":
                self.hide_to_tray()
                event.ignore()
            else:
                if self.tray_icon:
                    self.tray_icon.hide()
                event.accept()
        except Exception as e:
            print(f"关闭事件错误: {e}")
            event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_view == "grid":
            notes = self.filtered_notes if self.filtered_notes else self.current_notes
            if notes:
                QTimer.singleShot(50, lambda: self.refresh_grid_view(notes))


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

    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    try:
        icons_dir = "icons"
        if not os.path.exists(icons_dir):
            os.makedirs(icons_dir, exist_ok=True)
        window = MainWindow()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序启动错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()