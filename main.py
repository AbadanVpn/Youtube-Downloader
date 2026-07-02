#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import threading
import traceback
import signal
import subprocess
import time
from datetime import datetime

# --- 🛑 حل ریشه‌ای و قطعی باز شدن پنجره سیاه ترمینال در ویندوز به محض اجرا 🛑 ---
if sys.platform.startswith('win'):
    import ctypes
    kernel32 = ctypes.WinDLL('kernel32')
    user32 = ctypes.WinDLL('user32')
    hWnd = kernel32.GetConsoleWindow()
    if hWnd:
        user32.ShowWindow(hWnd, 0)
        
    myappid = 'mycompany.youtubedownloader.xray.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

from PySide6.QtCore import Qt, Signal, QObject, QByteArray, QRectF, QTimer, QUrl
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QRadioButton, QButtonGroup, QProgressBar, QMessageBox, 
                             QFileDialog, QTimeEdit, QDialog, QListWidget, QListWidgetItem)

try:
    from yt_dlp import YoutubeDL
except ImportError:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Error", "Please install yt-dlp first:\npip install yt-dlp")
    sys.exit()

# 🎨 وارد کردن آیکون‌های متنیِ بومی شده پروژه بدون وابستگی خارجی 🎨
try:
    import icons
except ImportError:
    app = QApplication(sys.argv)
    QMessageBox.critical(None, "Error", "Missing 'icons.py' file next to this script!")
    sys.exit()

FFMPEG_PATH = r"C:\ffmpeg\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"

MAX_CONCURRENT_DOWNLOADS = 3

LANGUAGES = {
    "fa": {
        "title": "داشبورد هوشمند دانلود از یوتیوب",
        "auto": " هوشمند (Auto)",
        "url_title": " آدرس ویدئو، موزیک یا پلی‌لیست یوتیوب",
        "path_title": " محل ذخیره فایلهای خروجی",
        "change_path": "انتخاب مسیر",
        "structure_title": " نوع ساختار فایل خروجی",
        "video_mode": "🎬 ویدئو کامل (Video)",
        "audio_mode": "🎵 استخراج صدا (Audio MP3)",
        "quality_title": " انتخاب سطح کیفیت",
        "monitor_title": " مانیتورینگ وضعیت هسته دانلود",
        "ready": "آماده برای دانلود جدید",
        "speed": "سرعت: 0 KB/s",
        "download_btn": " شروع دانلود آنی",
        "stop_btn": " توقف دانلود",
        "pause_btn": " مکث",
        "resume_btn": " ادامه دانلود",
        "processing": " در حال پردازش...",
        "connecting": "اتصال به شبکه یوتیوب...",
        "success_title": "موفقیت",
        "success_msg": "دانلود با موفقیت به پایان رسید.",
        "error_title": "خطای سیستم",
        "url_empty": "لطفاً آدرس یوتیوب را وارد کنید!",
        "stopped_msg": "دانلود توسط کاربر متوقف شد.",
        "light_mode_text": " پوسته روشن",
        "dark_mode_text": " پوسته تاریک",
        "add_queue": "➕ افزودن به صف",
        "view_queue": "📋 مشاهده صف",
        "start_sched": "⏰ زمان‌بندی",
        "sched_active": "⏱️ منتظر رسیدن به ساعت مشخص شده...",
        "queue_empty": "صف دانلود خالی است!",
        "queue_count": "لینک‌های موجود در صف: {}",
        "queue_title": "📋 مدیریت صف دانلود",
        "delete_btn": "🗑️ حذف انتخاب شده",
        "clear_btn": "❌ پاکسازی کل صف",
        "close_btn": "🔒 بستن پنجره",
        "active_downloads": "دانلودهای فعال: {} از {}"
    },
    "en": {
        "title": "YouTube Downloader - Dashboard",
        "auto": " Smart (Auto)",
        "url_title": " YouTube Video/Music/Playlist URL",
        "path_title": " Output Download Directory",
        "change_path": "Browse",
        "structure_title": " Output File Structure Type",
        "video_mode": "🎬 Full Video (Video)",
        "audio_mode": "🎵 Extract Audio (Audio MP3)",
        "quality_title": " Select Quality Level",
        "monitor_title": " Download Core Status Monitor",
        "ready": "Ready for new download",
        "speed": "Speed: 0 KB/s",
        "download_btn": " Start Immediate Download",
        "stop_btn": " Stop Download",
        "pause_btn": " Pause",
        "resume_btn": " Resume",
        "processing": " Processing...",
        "connecting": "Connecting to YouTube...",
        "success_title": "Success",
        "success_msg": "Download completed successfully.",
        "error_title": "System Error",
        "url_empty": "YouTube URL is empty!",
        "stopped_msg": "Download stopped by user.",
        "light_mode_text": " Light Mode",
        "dark_mode_text": " Dark Mode",
        "add_queue": "Add Queue",
        "view_queue": "View Queue",
        "start_sched": "Scheduler",
        "sched_active": "Waiting for scheduled time...",
        "queue_empty": "Download queue is empty!",
        "queue_count": "URLs in Queue: {}",
        "queue_title": "Download Queue Management",
        "delete_btn": "Delete Selected",
        "clear_btn": "Clear Entire Queue",
        "close_btn": "Close Window",
        "active_downloads": "Active Downloads: {} of {}"
    }
}

class QueueDialog(QDialog):
    def __init__(self, parent, queue_list, current_lang, is_dark_mode, update_badge_callback):
        super().__init__(parent)
        self.queue_list = queue_list
        self.current_lang = current_lang
        self.is_dark_mode = is_dark_mode
        self.update_badge_callback = update_badge_callback
        
        self.setup_ui()
        self.apply_styles()
        self.refresh_list()

    def setup_ui(self):
        ln = LANGUAGES[self.current_lang]
        self.setWindowTitle(ln["queue_title"])
        self.setFixedSize(550, 400)
        
        layout_dir = Qt.RightToLeft if self.current_lang == "fa" else Qt.LeftToRight
        self.setLayoutDirection(layout_dir)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(12)

        self.title_lbl = QLabel(ln["queue_title"])
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.layout.addWidget(self.title_lbl)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("PopupQueueList")
        self.layout.addWidget(self.list_widget)

        btns_layout = QHBoxLayout()
        self.delete_btn = QPushButton(ln["delete_btn"])
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setObjectName("PopupDeleteBtn")
        self.delete_btn.clicked.connect(self.delete_selected)

        self.clear_btn = QPushButton(ln["clear_btn"])
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setObjectName("PopupClearBtn")
        self.clear_btn.clicked.connect(self.clear_all)

        self.close_btn = QPushButton(ln["close_btn"])
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setObjectName("PopupCloseBtn")
        self.close_btn.clicked.connect(self.close)

        btns_layout.addWidget(self.delete_btn)
        btns_layout.addWidget(self.clear_btn)
        btns_layout.addStretch()
        btns_layout.addWidget(self.close_btn)
        self.layout.addLayout(btns_layout)

    def refresh_list(self):
        self.list_widget.clear()
        for idx, item in enumerate(self.queue_list):
            mode_display = "🎬 Video" if item["mode"] == "video" else "🎵 Audio"
            display_text = f"{idx+1}. [{mode_display} - {item['quality']}] {item['url']}"
            self.list_widget.addItem(QListWidgetItem(display_text))

    def delete_selected(self):
        selected_row = self.list_widget.currentRow()
        if selected_row >= 0:
            self.queue_list.pop(selected_row)
            self.refresh_list()
            self.update_badge_callback()
        else:
            if not self.queue_list:
                QMessageBox.information(self, "Queue", LANGUAGES[self.current_lang]["queue_empty"])

    def clear_all(self):
        if self.queue_list:
            self.queue_list.clear()
            self.refresh_list()
            self.update_badge_callback()

    def apply_styles(self):
        if self.is_dark_mode:
            bg_main = "#0d0e12"
            bg_input = "#16171d"
            border_input = "#22232a"
            text_white = "#ffffff"
            bg_btn = "#1c1d24"
        else:
            bg_main = "#ffffff"
            bg_input = "#f1f3f5"
            border_input = "#e2e8f0"
            text_white = "#0f172a"
            bg_btn = "#e2e8f0"

        qss = f"""
            QDialog {{ background-color: {bg_main}; color: {text_white}; font-family: 'IRANSansMobile', 'Segoe UI'; }}
            QLabel {{ color: {text_white}; background: transparent; }}
            QListWidget#PopupQueueList {{ background-color: {bg_input}; border: 1px solid {border_input}; border-radius: 8px; color: {text_white}; padding: 5px; font-size: 13px; }}
            QPushButton#PopupDeleteBtn {{ background-color: {bg_btn}; color: #dc2626; border: 1px solid #dc2626; border-radius: 6px; padding: 7px 14px; font-weight: bold; font-size: 13px; }}
            QPushButton#PopupClearBtn {{ background-color: {bg_btn}; color: {text_white}; border: 1px solid {border_input}; border-radius: 6px; padding: 7px 14px; font-weight: bold; font-size: 13px; }}
            QPushButton#PopupCloseBtn {{ background-color: #4b5563; color: white; border: none; border-radius: 6px; padding: 7px 16px; font-weight: bold; font-size: 13px; }}
        """
        self.setStyleSheet(qss)


class DownloadSignals(QObject):
    progress = Signal(float, str)
    success = Signal(str)
    error = Signal(str)
    next_queue = Signal()

class PremiumXrayDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_lang = "fa"  
        self.is_dark_mode = True   
        self.is_stopped = False
        
        self.is_paused = False
        self.pause_cond = threading.Condition()

        self.download_queue = [] 
        self.active_threads_count = 0
        self.thread_lock = threading.Lock()
        self.is_multi_download = False  

        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self.check_scheduler_time)
        self.target_time = None
        self.is_scheduler_running = False

        self.setFixedSize(860, 710) 
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.selected_video = "720p"
        self.selected_audio = "320kbps"
        self.signals = DownloadSignals()
        
        self.signals.progress.connect(self.update_progress)
        self.signals.success.connect(self.download_success)
        self.signals.error.connect(self.download_error)
        self.signals.next_queue.connect(self.process_next_queue_item)
        
        self.apply_system_font() 
        self.set_application_logo() 
        self.setup_ui()
        self.apply_styles()
        self.update_language_ui()

    def apply_system_font(self):
        font = QFont("IRANSansMobile", 10)
        font.setFamilies(["IRANSansMobile", "Segoe UI"])
        font.setStyleStrategy(QFont.PreferAntialias)
        QApplication.setFont(font)

    # 🛠️ متد جادویی برای تبدیل متن متنی SVG به QIcon به همراه تغییر رنگ هوشمند المنت‌های بدون رنگ متناسب با تم پوسته
    def get_svg_icon(self, svg_content, color=None):
        if color:
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
            svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')
        else:
            default_color = "#ffffff" if self.is_dark_mode else "#0f172a"
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{default_color}"')
            svg_content = svg_content.replace('fill="currentColor"', f'fill="{default_color}"')
            
        byte_array = QByteArray(svg_content.encode('utf-8'))
        pixmap = QPixmap()
        pixmap.loadFromData(byte_array, "SVG")
        return QIcon(pixmap)

    def set_application_logo(self):
        self.setWindowIcon(self.get_svg_icon(icons.YOUTUBE_SVG))

    def setup_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(30, 20, 30, 20)
        self.main_layout.setSpacing(12)

        # ------------------ HEADER WITH CONTROLS & SOCIALS ------------------
        self.header_layout = QHBoxLayout()
        
        self.title_container = QWidget()
        self.title_container.setStyleSheet("background: transparent;")
        self.title_vbox = QVBoxLayout(self.title_container)
        self.title_vbox.setContentsMargins(0, 0, 0, 0)
        self.title_vbox.setSpacing(6)

        self.socials_layout = QHBoxLayout()
        self.socials_layout.setSpacing(10)
        
        self.github_btn = QPushButton()
        self.github_btn.setObjectName("SocialBtn")
        self.github_btn.setFixedSize(28, 28)
        self.github_btn.setCursor(Qt.PointingHandCursor)
        self.github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/AbadanVpn")))

        self.telegram_btn = QPushButton()
        self.telegram_btn.setObjectName("SocialBtn")
        self.telegram_btn.setFixedSize(28, 28)
        self.telegram_btn.setCursor(Qt.PointingHandCursor)
        self.telegram_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://t.me/abadanvpn")))

        self.socials_layout.addWidget(self.github_btn)
        self.socials_layout.addWidget(self.telegram_btn)
        self.socials_layout.addStretch()

        self.title_lbl = QLabel()
        self.title_lbl.setObjectName("HeaderTitle")
        
        self.title_vbox.addLayout(self.socials_layout)
        self.title_vbox.addWidget(self.title_lbl)

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(8)
        
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("TopBarBtn")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)

        self.bytes_label = QLabel()

        self.lang_btn = QPushButton("English")
        self.lang_btn.setObjectName("TopBarBtn")
        self.lang_btn.setCursor(Qt.PointingHandCursor)
        self.lang_btn.clicked.connect(self.toggle_language)

        self.auto_btn = QPushButton()
        self.auto_btn.setObjectName("AutoBtn")
        self.auto_btn.setCursor(Qt.PointingHandCursor)
        self.auto_btn.setCheckable(True)
        self.auto_btn.clicked.connect(self.set_auto_mode)
        
        self.controls_layout.addWidget(self.theme_btn)
        self.controls_layout.addWidget(self.lang_btn)
        self.controls_layout.addWidget(self.auto_btn)
        self.main_layout.addLayout(self.header_layout)

        # ------------------ URL CARD ------------------
        self.url_card = QWidget()
        self.url_card.setObjectName("Card")
        self.url_layout = QVBoxLayout(self.url_card)
        url_header = QHBoxLayout()
        self.url_icon_lbl = QLabel()
        self.url_title = QLabel()
        self.url_title.setObjectName("CardTitleBlue")
        url_header.addWidget(self.url_icon_lbl)
        url_header.addWidget(self.url_title)
        url_header.addStretch()
        self.url_layout.addLayout(url_header)
        
        self.url_input_layout = QHBoxLayout()
        self.paste_btn = QPushButton()
        self.paste_btn.setObjectName("PasteButton")
        self.paste_btn.setCursor(Qt.PointingHandCursor)
        self.paste_btn.clicked.connect(self.paste_url)
        self.url_entry = QLineEdit()
        self.url_entry.setPlaceholderText("https://youtube.com/watch?v=...")
        self.url_input_layout.addWidget(self.paste_btn)
        self.url_input_layout.addWidget(self.url_entry)
        self.url_layout.addLayout(self.url_input_layout)
        
        sched_inline_layout = QHBoxLayout()
        sched_inline_layout.setSpacing(8)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setObjectName("InlineTime")
        self.time_edit.setTime(datetime.now().time())
        self.time_edit.setLayoutDirection(Qt.LeftToRight)
        self.time_edit.setAlignment(Qt.AlignCenter)
        
        self.add_queue_btn = QPushButton()
        self.add_queue_btn.setObjectName("SecondaryButtonInline")
        self.add_queue_btn.clicked.connect(self.add_to_queue)
        
        self.view_queue_btn = QPushButton()
        self.view_queue_btn.setObjectName("ViewQueueButtonInline")
        self.view_queue_btn.clicked.connect(self.open_queue_popup)
        
        self.start_sched_btn = QPushButton()
        self.start_sched_btn.setObjectName("SchedActionButtonInline")
        self.start_sched_btn.clicked.connect(self.toggle_scheduler)

        self.queue_badge = QLabel()
        self.queue_badge.setObjectName("QueueBadge")
        
        sched_inline_layout.addWidget(self.time_edit, 1)
        sched_inline_layout.addWidget(self.add_queue_btn, 1)
        sched_inline_layout.addWidget(self.view_queue_btn, 1)
        sched_inline_layout.addWidget(self.start_sched_btn, 1)
        sched_inline_layout.addSpacing(15)
        sched_inline_layout.addWidget(self.queue_badge)
        self.url_layout.addLayout(sched_inline_layout)
        
        self.main_layout.addWidget(self.url_card)

        # ------------------ PATH CARD ------------------
        self.path_card = QWidget()
        self.path_card.setObjectName("Card")
        self.path_layout = QVBoxLayout(self.path_card)
        path_header = QHBoxLayout()
        self.path_icon_lbl = QLabel()
        self.path_title = QLabel()
        self.path_title.setObjectName("CardTitleGray")
        path_header.addWidget(self.path_icon_lbl)
        path_header.addWidget(self.path_title)
        path_header.addStretch()
        self.path_layout.addLayout(path_header)
        
        self.path_input_layout = QHBoxLayout()
        self.change_path_btn = QPushButton()
        self.change_path_btn.setObjectName("SecondaryButton")
        self.change_path_btn.setCursor(Qt.PointingHandCursor)
        self.change_path_btn.clicked.connect(self.choose_directory)
        self.path_entry = QLineEdit(self.download_path)
        self.path_entry.setReadOnly(True)
        self.path_input_layout.addWidget(self.change_path_btn)
        self.path_input_layout.addWidget(self.path_entry)
        self.path_layout.addLayout(self.path_input_layout)
        self.main_layout.addWidget(self.path_card)

        # ------------------ MODE CARD ------------------
        self.mode_card = QWidget()
        self.mode_card.setObjectName("Card")
        self.mode_layout = QVBoxLayout(self.mode_card)
        struct_header = QHBoxLayout()
        self.struct_icon_lbl = QLabel()
        self.structure_title = QLabel()
        self.structure_title.setObjectName("CardTitleGray")
        struct_header.addWidget(self.struct_icon_lbl)
        struct_header.addStretch()
        self.mode_layout.addLayout(struct_header)
        
        self.mode_rb_layout = QHBoxLayout()
        self.rb_audio = QRadioButton()
        self.rb_video = QRadioButton()
        self.rb_video.setChecked(True)
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.rb_video)
        self.mode_group.addButton(self.rb_audio)
        self.mode_group.buttonClicked.connect(self.update_mode_ui)
        self.mode_rb_layout.addWidget(self.rb_audio)
        self.mode_rb_layout.addWidget(self.rb_video)
        self.mode_layout.addLayout(self.mode_rb_layout)
        self.main_layout.addWidget(self.mode_card)

        # ------------------ QUALITY CARD ------------------
        self.quality_card = QWidget()
        self.quality_card.setObjectName("Card")
        self.qual_layout = QVBoxLayout(self.quality_card)
        qual_header = QHBoxLayout()
        self.qual_icon_lbl = QLabel()
        self.quality_title = QLabel()
        self.quality_title.setObjectName("CardTitleGray")
        qual_header.addWidget(self.qual_icon_lbl)
        qual_header.addStretch()
        self.qual_layout.addLayout(qual_header)
        
        self.video_frame = QWidget()
        self.video_frame.setStyleSheet("background-color: transparent;")
        self.v_qual_layout = QHBoxLayout(self.video_frame)
        self.v_qual_layout.setContentsMargins(0, 0, 0, 0)
        self.v_buttons = []
        
        quality_list = ["480p", "720p", "1080p (HD)", "1440p (2K)", "2160p (8K)", "🎵 فقط صدا (Audio)"]
        for q in quality_list:
            btn = QPushButton(q)
            btn.setObjectName("QualButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, x=q: self.select_quality(x, "video"))
            self.v_qual_layout.addWidget(btn)
            self.v_buttons.append(btn)
        self.qual_layout.addWidget(self.video_frame)
        
        self.audio_frame = QWidget()
        self.audio_frame.setStyleSheet("background-color: transparent;")
        self.a_qual_layout = QHBoxLayout(self.audio_frame)
        self.a_qual_layout.setContentsMargins(0, 0, 0, 0)
        self.a_buttons = []
        for q in ["128kbps", "192kbps", "320kbps"]:
            btn = QPushButton(q)
            btn.setObjectName("QualButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, x=q: self.select_quality(x, "audio"))
            self.a_qual_layout.addWidget(btn)
            self.a_buttons.append(btn)
        self.qual_layout.addWidget(self.audio_frame)
        self.main_layout.addWidget(self.quality_card)
        
        self.select_quality("720p", "video")
        self.select_quality("320kbps", "audio")

        # ------------------ MONITORING CARD ------------------
        self.prog_card = QWidget()
        self.prog_card.setObjectName("Card")
        prog_layout = QVBoxLayout(self.prog_card)
        mon_header = QHBoxLayout()
        self.mon_icon_lbl = QLabel()
        self.monitor_title = QLabel()
        self.monitor_title.setObjectName("CardTitleGray")
        mon_header.addWidget(self.mon_icon_lbl)
        mon_header.addStretch()
        prog_layout.addLayout(mon_header)
        
        self.info_layout = QHBoxLayout()
        self.speed_label = QLabel()
        self.speed_label.setObjectName("SpeedLabel")
        self.info_layout.addWidget(self.speed_label)
        prog_layout.addLayout(self.info_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12) 
        prog_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self.prog_card)

        # ------------------ ACTION BUTTONS WITH PAUSE ------------------
        buttons_layout = QHBoxLayout()
        
        self.stop_btn = QPushButton()
        self.stop_btn.setObjectName("StopButton")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False) 
        self.stop_btn.clicked.connect(self.stop_download)
        buttons_layout.addWidget(self.stop_btn, 1)

        self.pause_btn = QPushButton()
        self.pause_btn.setObjectName("PauseButton")
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        buttons_layout.addWidget(self.pause_btn, 1)

        self.download_btn = QPushButton()
        self.download_btn.setObjectName("DownloadButton")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(self.start_download)
        buttons_layout.addWidget(self.download_btn, 2) 
        
        self.main_layout.addLayout(buttons_layout)
        self.update_mode_ui()
        self.update_badge()

    def update_badge(self):
        txt = LANGUAGES[self.current_lang]["queue_count"].format(len(self.download_queue))
        self.queue_badge.setText(txt)

    def open_queue_popup(self):
        dialog = QueueDialog(self, self.download_queue, self.current_lang, self.is_dark_mode, self.update_badge)
        dialog.exec()

    def add_to_queue(self):
        url = self.url_entry.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", LANGUAGES[self.current_lang]["url_empty"])
            return
        
        actual_mode = "video" if self.rb_video.isChecked() else "audio"
        quality = self.selected_video if actual_mode == "video" else self.selected_audio
        
        item_data = {
            "url": url,
            "mode": actual_mode,
            "quality": quality,
            "path": self.path_entry.text()
        }
        self.download_queue.append(item_data)
        self.url_entry.clear()
        self.update_badge()

    def toggle_scheduler(self):
        ln = LANGUAGES[self.current_lang]
        if not self.is_scheduler_running:
            if not self.download_queue:
                QMessageBox.warning(self, "Warning", ln["queue_empty"])
                return
            self.target_time = self.time_edit.time()
            self.is_scheduler_running = True
            self.scheduler_timer.start(1000)
            self.start_sched_btn.setText(ln["stop_btn"])
            self.start_sched_btn.setStyleSheet("background-color: #dc2626; color: white;")
            self.speed_label.setText(ln["sched_active"])
            self.download_btn.setEnabled(False)
        else:
            self.is_scheduler_running = False
            self.scheduler_timer.stop()
            self.start_sched_btn.setText(ln["start_sched"])
            self.start_sched_btn.setStyleSheet("")
            self.speed_label.setText(ln["ready"])
            self.download_btn.setEnabled(True)

    def check_scheduler_time(self):
        current_time = datetime.now().time()
        if (current_time.hour == self.target_time.hour() and 
            current_time.minute == self.target_time.minute()):
            self.scheduler_timer.stop()
            self.is_scheduler_running = False
            self.start_sched_btn.setText(LANGUAGES[self.current_lang]["start_sched"])
            self.start_sched_btn.setStyleSheet("")
            self.is_multi_download = True  
            self.signals.next_queue.emit()

    def process_next_queue_item(self):
        with self.thread_lock:
            if self.is_stopped:
                return
            
            if self.active_threads_count >= MAX_CONCURRENT_DOWNLOADS or not self.download_queue:
                if self.active_threads_count == 0 and not self.download_queue:
                    self.reset_ui()
                return

            item = self.download_queue.pop(0)
            self.active_threads_count += 1

        self.update_badge()
        ln = LANGUAGES[self.current_lang]
        
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)  
        self.pause_btn.setEnabled(True)
        
        if self.is_multi_download:
            self.speed_label.setText(ln["active_downloads"].format(self.active_threads_count, MAX_CONCURRENT_DOWNLOADS))
        else:
            self.speed_label.setText(ln["connecting"])

        thread = threading.Thread(target=self.download_worker, args=(item["url"], item["path"], item["mode"], item["quality"]), daemon=True)
        thread.start()

        if self.is_multi_download:
            QTimer.singleShot(100, self.signals.next_queue.emit)

    def toggle_pause(self):
        ln = LANGUAGES[self.current_lang]
        with self.pause_cond:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_btn.setText(ln["resume_btn"])
                self.pause_btn.setStyleSheet("background-color: #d97706; color: white;")
            else:
                self.pause_btn.setText(ln["pause_btn"])
                self.pause_btn.setStyleSheet("background-color: #ca8a04; color: white;")
                self.pause_cond.notify_all()

    def toggle_language(self):
        self.current_lang = "en" if self.current_lang == "fa" else "fa"
        self.lang_btn.setText("فارسی" if self.current_lang == "en" else "English")
        self.update_language_ui()
        self.update_badge()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_styles()
        self.update_language_ui()

    def update_language_ui(self):
        ln = LANGUAGES[self.current_lang]
        layout_dir = Qt.RightToLeft if self.current_lang == "fa" else Qt.LeftToRight
        self.main_widget.setLayoutDirection(layout_dir)
        
        self.setWindowTitle(ln["title"])
        self.title_lbl.setText(ln["title"])
        self.auto_btn.setText(ln["auto"])
        self.url_title.setText(ln["url_title"])
        self.path_title.setText(ln["path_title"])
        self.change_path_btn.setText(ln["change_path"])
        self.structure_title.setText(ln["structure_title"])
        self.rb_video.setText(ln["video_mode"])
        self.rb_audio.setText(ln["audio_mode"])
        self.quality_title.setText(ln["quality_title"])
        self.monitor_title.setText(ln["monitor_title"])
        
        # رندر و تنظیم داینامیک تمامی آیکون‌های گرافیکی بر اساس تم فعلی و زبان انتخابی
        icon_color = "#ffffff" if self.is_dark_mode else "#0f172a"
        
        self.github_btn.setIcon(self.get_svg_icon(icons.GITHUB_SVG, icon_color))
        self.telegram_btn.setIcon(self.get_svg_icon(icons.TELEGRAM_SVG, "#229ED9"))
        self.lang_btn.setIcon(self.get_svg_icon(icons.LANGUAGE_SVG, icon_color))
        self.auto_btn.setIcon(self.get_svg_icon(icons.BOLT_SVG, icon_color))
        
        self.url_icon_lbl.setPixmap(self.get_svg_icon(icons.LINK_SVG).pixmap(20, 20))
        self.paste_btn.setIcon(self.get_svg_icon(icons.CLIPBOARD_SVG, "#3b82f6"))
        
        self.path_icon_lbl.setPixmap(self.get_svg_icon(icons.FOLDER_SVG, icon_color).pixmap(20, 20))
        self.change_path_btn.setIcon(self.get_svg_icon(icons.FOLDER_OPEN_SVG, icon_color))
        
        self.struct_icon_lbl.setPixmap(self.get_svg_icon(icons.SETTINGS_SVG, icon_color).pixmap(20, 20))
        self.qual_icon_lbl.setPixmap(self.get_svg_icon(icons.TRANSFORM_SVG, icon_color).pixmap(20, 20))
        self.mon_icon_lbl.setPixmap(self.get_svg_icon(icons.ACTIVITY_SVG, icon_color).pixmap(20, 20))
        
        self.stop_btn.setIcon(self.get_svg_icon(icons.PLAYER_STOP_SVG, "#ffffff"))
        self.pause_btn.setIcon(self.get_svg_icon(icons.PLAYER_PAUSE_SVG, "#ffffff"))
        self.download_btn.setIcon(self.get_svg_icon(icons.DOWNLOAD_SVG, "#ffffff"))
        
        if self.active_threads_count > 0:
            if self.is_multi_download:
                self.speed_label.setText(ln["active_downloads"].format(self.active_threads_count, MAX_CONCURRENT_DOWNLOADS))
        else:
            self.speed_label.setText(ln["speed"])
            
        self.stop_btn.setText(ln["stop_btn"])
        
        if not self.is_paused:
            self.pause_btn.setText(ln["pause_btn"])
        else:
            self.pause_btn.setText(ln["resume_btn"])

        self.add_queue_btn.setText(ln["add_queue"])
        self.view_queue_btn.setText(ln["view_queue"])
        
        if not self.is_scheduler_running:
            self.start_sched_btn.setText(ln["start_sched"])

        if self.is_dark_mode:
            self.theme_btn.setText(ln["light_mode_text"])
            self.theme_btn.setIcon(self.get_svg_icon(icons.SUN_SVG, icon_color))
        else:
            self.theme_btn.setText(ln["dark_mode_text"])
            self.theme_btn.setIcon(self.get_svg_icon(icons.MOON_SVG, icon_color))

        if self.download_btn.isEnabled():
            self.download_btn.setText(ln["download_btn"])
        
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            
        if self.current_lang == "fa":
            self.socials_layout.setDirection(QHBoxLayout.RightToLeft)
            self.header_layout.addLayout(self.controls_layout)
            self.header_layout.addStretch()
            self.header_layout.addWidget(self.title_container, alignment=Qt.AlignRight)
        else:
            self.socials_layout.setDirection(QHBoxLayout.LeftToRight)
            self.header_layout.addWidget(self.title_container, alignment=Qt.AlignLeft)
            self.header_layout.addStretch()
            self.header_layout.addLayout(self.controls_layout)

    def apply_styles(self):
        if self.is_dark_mode:
            bg_main = "#060709"
            bg_card = "#0d0e12"
            bg_input = "#16171d"
            border_input = "#22232a"
            text_white = "#ffffff"
            text_gray = "#9ca3af"
            bg_btn = "#1c1d24"
            progress_trough = "#1b1c21"
            progress_chunk = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:0.5 #3b82f6, stop:1 #60a5fa)"
            arrow_color = "#9ca3af"
        else:
            bg_main = "#f4f5f7"
            bg_card = "#ffffff"
            bg_input = "#f1f3f5"
            border_input = "#e2e8f0"
            text_white = "#0f172a"
            text_gray = "#64748b"
            bg_btn = "#e2e8f0"
            progress_trough = "#cbd5e1"
            progress_chunk = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:0.5 #2563eb, stop:1 #3b82f6)"
            arrow_color = "#64748b"

        qss = f"""
            QWidget {{ background-color: {bg_main}; color: {text_white}; font-family: 'IRANSansMobile', 'Segoe UI'; }}
            QLabel {{ background-color: transparent; color: {text_white}; }}
            #HeaderTitle {{ color: {text_white}; font-size: 17px; font-weight: bold; background-color: transparent; }}
            #TopBarBtn {{ background-color: {bg_btn}; color: {text_white}; border: 1px solid {border_input}; border-radius: 8px; padding: 6px 14px; font-weight: bold; }}
            #SocialBtn {{ background-color: {bg_btn}; border: 1px solid {border_input}; border-radius: 6px; }}
            #SocialBtn:hover {{ background-color: {border_input}; }}
            #Card {{ background-color: {bg_card}; border: 1px solid {border_input}; border-radius: 12px; }}
            #Card QLabel {{ background-color: transparent; }}
            #CardTitleBlue {{ color: #3b82f6; font-size: 14px; font-weight: bold; background-color: transparent; }}
            #CardTitleGray {{ color: {text_gray}; font-size: 14px; font-weight: bold; background-color: transparent; }}
            QLineEdit {{ background-color: {bg_input}; color: {text_white}; border: 1px solid {border_input}; border-radius: 8px; padding: 10px; font-size: 14px; }}
            
            QTimeEdit#InlineTime {{ background-color: {bg_input}; color: {text_white}; border: 1px solid {border_input}; border-radius: 6px; padding: 5px; font-size: 13px; }}
            QTimeEdit#InlineTime::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 18px; border-left: 1px solid {border_input}; border-bottom: 1px solid {border_input}; background: {bg_btn}; border-top-right-radius: 6px; }}
            QTimeEdit#InlineTime::up-arrow {{ image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid {arrow_color}; width: 0; height: 0; }}
            QTimeEdit#InlineTime::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 18px; border-left: 1px solid {border_input}; background: {bg_btn}; border-bottom-right-radius: 6px; }}
            QTimeEdit#InlineTime::down-arrow {{ image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {arrow_color}; width: 0; height: 0; }}

            QPushButton#PasteButton {{ background-color: {bg_btn}; color: #3b82f6; border: 1px solid {border_input}; border-radius: 8px; padding: 8px 16px; }}
            QPushButton#SecondaryButton {{ background-color: {bg_btn}; color: {text_white}; border: 1px solid {border_input}; border-radius: 8px; padding: 8px 18px; font-weight: bold; }}
            QPushButton#SecondaryButtonInline {{ background-color: {bg_btn}; color: #3b82f6; border: 1px solid {border_input}; border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: bold; }}
            QPushButton#ViewQueueButtonInline {{ background-color: {bg_btn}; color: #10b981; border: 1px solid {border_input}; border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: bold; }}
            QPushButton#SchedActionButtonInline {{ background-color: #5b21b6; color: #ffffff; border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: bold; }}
            #QueueBadge {{ color: #a78bfa; font-weight: bold; font-size: 13px; background-color: transparent; }}
            QRadioButton {{ color: {text_white}; font-size: 14px; background-color: transparent; }}
            QPushButton#QualButton {{ background-color: {bg_btn}; color: {text_gray}; border: 1px solid {border_input}; border-radius: 8px; padding: 8px 20px; font-weight: bold; }}
            QPushButton#QualButton:checked {{ background-color: #3b82f6; color: #ffffff; }}
            QPushButton#AutoBtn {{ background-color: {bg_btn}; color: {text_gray}; border: 1px solid {border_input}; border-radius: 8px; padding: 7px 16px; }}
            QPushButton#AutoBtn:checked {{ background-color: #581c87; color: #ffffff; }}
            #SpeedLabel {{ color: #a78bfa; font-size: 14px; font-weight: bold; background-color: transparent; }}
            QProgressBar {{ background-color: {progress_trough}; border: none; border-radius: 6px; }}
            QProgressBar::chunk {{ background-color: {progress_chunk}; border-radius: 6px; }}
            QPushButton#DownloadButton {{ background-color: #059669; color: #ffffff; font-size: 15px; font-weight: bold; padding: 14px; border-radius: 10px; }}
            QPushButton#StopButton {{ background-color: #dc2626; color: #ffffff; font-size: 15px; font-weight: bold; padding: 14px; border-radius: 10px; }}
            QPushButton#PauseButton {{ background-color: #ca8a04; color: #ffffff; font-size: 15px; font-weight: bold; padding: 14px; border-radius: 10px; }}
            QPushButton#PauseButton:disabled {{ background-color: #713f12; color: #9ca3af; }}
        """
        self.setStyleSheet(qss)

    def set_auto_mode(self):
        if self.auto_btn.isChecked():
            self.video_frame.hide()
            self.auto_btn.setChecked(True)
        else:
            self.update_mode_ui()

    def update_mode_ui(self):
        if self.auto_btn.isChecked():
            return
        if self.rb_video.isChecked():
            self.video_frame.show()
            self.audio_frame.hide()
        else:
            self.audio_frame.show()
            self.video_frame.hide()

    def select_quality(self, q, mode):
        buttons = self.v_buttons if mode == "video" else self.a_buttons
        for btn in buttons:
            if mode == "video":
                match_target = re.search(r'\d+p', q)
                match_btn = re.search(r'\d+p', btn.text())
                if match_target and match_btn and match_target.group() == match_btn.group():
                    btn.setChecked(True)
                else:
                    btn.setChecked(btn.text() == q)
            else:
                btn.setChecked(btn.text() == q)
                
        if mode == "video":
            self.selected_video = q
        else:
            self.selected_audio = q

    def choose_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder", self.path_entry.text())
        if path:
            self.path_entry.setText(path)

    def paste_url(self):
        self.url_entry.setText(QApplication.clipboard().text())

    def start_download(self):
        ln = LANGUAGES[self.current_lang]
        url = self.url_entry.text().strip()
        
        if not url and self.download_queue:
            self.is_stopped = False
            self.is_multi_download = True 
            self.signals.next_queue.emit()
            return
            
        if not url:
            QMessageBox.warning(self, "Warning", ln["url_empty"])
            return

        save_path = self.path_entry.text()
        os.makedirs(save_path, exist_ok=True)

        actual_mode = "video" if self.rb_video.isChecked() else "audio"
        quality = self.selected_video if actual_mode == "video" else self.selected_audio

        item_data = {
            "url": url,
            "mode": actual_mode,
            "quality": quality,
            "path": save_path
        }
        
        if self.download_queue:
            self.is_multi_download = True
            self.download_queue.insert(0, item_data)
        else:
            self.is_multi_download = False
            self.download_queue.insert(0, item_data)
        
        self.url_entry.clear()
        self.is_stopped = False
        self.signals.next_queue.emit()

    def stop_download(self):
        self.is_stopped = True
        with self.pause_cond:
            self.is_paused = False
            self.pause_cond.notify_all()
            
        with self.thread_lock:
            self.download_queue.clear()
            self.active_threads_count = 0
            
        self.signals.error.emit(LANGUAGES[self.current_lang]["stopped_msg"])

    def download_worker(self, url, save_path, actual_mode, quality):
        try:
            if self.auto_btn.isChecked():
                actual_mode = "audio" if any(k in url.lower() for k in ["music", "audio", "podcast"]) else "video"

            if actual_mode == "video" and "فقط صدا" in quality:
                actual_mode = "audio_forced"

            startupinfo = None
            if sys.platform.startswith('win'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            ydl_opts = {
                'outtmpl': os.path.join(save_path, '%(playlist_title)s/%(title)s.%(ext)s' if 'list=' in url else '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'nocheckcertificate': True,
                'yes_playlist': True,
            }
            if sys.platform.startswith('win'):
                ydl_opts['startupinfo'] = startupinfo

            if actual_mode in ["audio", "audio_forced"]:
                br = quality.replace("kbps", "") if "kbps" in quality else "320"
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': br}]
                })
            else:
                match = re.search(r'\d+', quality)
                height = match.group() if match else "720"
                ydl_opts['format'] = f"bestvideo[height<={height}]+bestaudio/best/best[height<={height}]/best"

            if os.path.exists(FFMPEG_PATH):
                ydl_opts['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)

            with YoutubeDL(ydl_opts) as ydl:
                if not self.is_stopped:
                    ydl.download([url])

            if not self.is_stopped:
                self.signals.success.emit(url)
        except Exception as e:
            if not self.is_stopped:
                self.signals.error.emit(f"{url} -> {str(e)}")

    def progress_hook(self, d):
        with self.pause_cond:
            while self.is_paused and not self.is_stopped:
                self.pause_cond.wait(0.5)

        if self.is_stopped:
            raise Exception("Stopped by user")
            
        if d['status'] == 'downloading':
            try:
                percent_str = d.get('_percent_str', '0')
                clean_percent = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).replace('%', '').strip()
                percent = float(clean_percent)
                speed = d.get('_speed_str', '0 KB/s')
                
                v_title = d.get('info_dict', {}).get('title', 'Video')
                if len(v_title) > 20: v_title = v_title[:17] + "..."

                ln = LANGUAGES[self.current_lang]
                
                if self.is_multi_download:
                    speed_txt = (f"[{v_title}] ⚡ {speed} | 📊 {percent:.1f}%\n"
                                 f"{ln['active_downloads'].format(self.active_threads_count, MAX_CONCURRENT_DOWNLOADS)}")
                else:
                    speed_txt = f"[{v_title}] ⚡ {speed} | 📊 {percent:.1f}%"
                
                self.signals.progress.emit(percent, speed_txt)
            except:
                pass

    def update_progress(self, val, speed_text):
        self.progress_bar.setValue(int(val))
        self.speed_label.setText(speed_text)

    def download_success(self, url):
        with self.thread_lock:
            if self.active_threads_count > 0:
                self.active_threads_count -= 1
        self.signals.next_queue.emit()

    def download_error(self, msg):
        with self.thread_lock:
            if self.active_threads_count > 0:
                self.active_threads_count -= 1
        self.signals.next_queue.emit()

    def reset_ui(self):
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.is_paused = False
        self.is_multi_download = False
        self.update_language_ui()
        self.progress_bar.setValue(0)
        self.update_mode_ui()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PremiumXrayDownloader()
    window.show()
    sys.exit(app.exec())
