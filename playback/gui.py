import asyncio
import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from engine import PlaybackEngine


class SignalLogHandler(logging.Handler):
    def __init__(self, signal: Signal) -> None:
        super().__init__()
        self.signal = signal
        self.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )

    def emit(self, record: logging.LogRecord) -> None:
        self.signal.emit(self.format(record))


class WorkerThread(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)
    login_ready_signal = Signal()

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__()
        self.config = config
        self.engine: Optional[PlaybackEngine] = None
        self._login_continue_event = threading.Event()

    def run(self) -> None:
        try:
            asyncio.run(self._run_async())
        except Exception as e:
            self.finished_signal.emit(False, str(e))

    async def _run_async(self) -> None:
        handler = SignalLogHandler(self.log_signal)
        logger_names = ["engine", "video_detector"]
        loggers = [logging.getLogger(name) for name in logger_names]
        for logger in loggers:
            logger.handlers = [h for h in logger.handlers if not isinstance(h, SignalLogHandler)]
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
        try:
            self.engine = PlaybackEngine(
                script_path=self.config["script_path"],
                headless=self.config["headless"],
                slow_mo=self.config["slow_mo"],
                on_error=self.config["on_error"],
                browser=self.config["browser"],
                wait_for_enter=self.config["wait_for_enter"],
                use_step_url=self.config["use_step_url"],
                auto_wait_video_after_click=self.config["auto_wait_video_after_click"],
                video_start_timeout=self.config["video_start_timeout"],
                video_end_timeout=self.config["video_end_timeout"],
                wait_for_start_signal=self._wait_for_gui_continue,
            )
            await self.engine.run()
            self.finished_signal.emit(True, "回放完成")
        except Exception as e:
            self.finished_signal.emit(False, str(e))
        finally:
            for logger in loggers:
                logger.removeHandler(handler)

    def stop(self) -> None:
        self._login_continue_event.set()
        self.requestInterruption()

    def continue_after_login(self) -> None:
        self._login_continue_event.set()

    async def _wait_for_gui_continue(self) -> None:
        self.login_ready_signal.emit()
        await asyncio.to_thread(self._login_continue_event.wait)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("网课学习助手 - 回放控制面板")
        self.setMinimumSize(900, 700)

        self.worker: Optional[WorkerThread] = None

        self._init_ui()
        self._init_logging()
        self._load_default_config()

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        config_widget = self._create_config_widget()
        splitter.addWidget(config_widget)
        log_widget = self._create_log_widget()
        splitter.addWidget(log_widget)
        splitter.setSizes([400, 300])
        main_layout.addWidget(splitter)
        control_layout = self._create_control_buttons()
        main_layout.addLayout(control_layout)

    def _create_config_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        script_group = QGroupBox("脚本配置")
        script_layout = QHBoxLayout()

        self.script_path_edit = QLineEdit()
        self.script_path_edit.setPlaceholderText("请选择录制脚本 JSON 文件...")
        script_layout.addWidget(self.script_path_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_script)
        script_layout.addWidget(browse_btn)

        script_group.setLayout(script_layout)
        layout.addWidget(script_group)

        params_group = QGroupBox("运行参数")
        params_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("浏览器:"))
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["edge", "chromium"])
        row1.addWidget(self.browser_combo)

        row1.addWidget(QLabel("错误处理:"))
        self.on_error_combo = QComboBox()
        self.on_error_combo.addItems(["stop", "skip"])
        row1.addWidget(self.on_error_combo)

        row1.addWidget(QLabel("日志级别:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        row1.addWidget(self.log_level_combo)

        row1.addStretch()
        params_layout.addLayout(row1)

        row2 = QHBoxLayout()

        self.headless_check = QCheckBox("无头模式")
        row2.addWidget(self.headless_check)

        self.wait_enter_check = QCheckBox("登录后等待回车")
        self.wait_enter_check.setChecked(True)
        row2.addWidget(self.wait_enter_check)

        self.use_step_url_check = QCheckBox("使用脚本URL导航")
        row2.addWidget(self.use_step_url_check)

        self.auto_wait_video_check = QCheckBox("点击后自动等视频")
        self.auto_wait_video_check.setChecked(True)
        row2.addWidget(self.auto_wait_video_check)

        row2.addStretch()
        params_layout.addLayout(row2)

        row3 = QHBoxLayout()

        row3.addWidget(QLabel("慢动作延迟(ms):"))
        self.slow_mo_spin = QSpinBox()
        self.slow_mo_spin.setRange(0, 10000)
        self.slow_mo_spin.setSingleStep(100)
        row3.addWidget(self.slow_mo_spin)

        row3.addWidget(QLabel("视频启动超时(s):"))
        self.video_start_spin = QSpinBox()
        self.video_start_spin.setRange(1, 300)
        self.video_start_spin.setValue(8)
        row3.addWidget(self.video_start_spin)

        row3.addWidget(QLabel("视频结束超时(s):"))
        self.video_end_spin = QSpinBox()
        self.video_end_spin.setRange(1, 86400)
        self.video_end_spin.setValue(7200)
        row3.addWidget(self.video_end_spin)

        row3.addStretch()
        params_layout.addLayout(row3)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        config_btn_layout = QHBoxLayout()

        save_config_btn = QPushButton("保存配置")
        save_config_btn.clicked.connect(self._save_config)
        config_btn_layout.addWidget(save_config_btn)

        load_config_btn = QPushButton("加载配置")
        load_config_btn.clicked.connect(self._load_config)
        config_btn_layout.addWidget(load_config_btn)

        config_btn_layout.addStretch()
        layout.addLayout(config_btn_layout)

        layout.addStretch()
        return widget

    def _create_log_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_text)

        log_btn_layout = QHBoxLayout()

        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_btn_layout.addWidget(clear_log_btn)

        save_log_btn = QPushButton("保存日志")
        save_log_btn.clicked.connect(self._save_log)
        log_btn_layout.addWidget(save_log_btn)

        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        return widget

    def _create_control_buttons(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ 开始回放")
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-size: 14px; }")
        self.start_btn.clicked.connect(self._start_playback)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 10px; font-size: 14px; }")
        self.stop_btn.clicked.connect(self._stop_playback)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        self.continue_btn = QPushButton("登录完成，开始回放")
        self.continue_btn.setStyleSheet("QPushButton { background-color: #1976D2; color: white; padding: 10px; font-size: 14px; }")
        self.continue_btn.clicked.connect(self._continue_after_login)
        self.continue_btn.setEnabled(False)
        layout.addWidget(self.continue_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("就绪")
        layout.addWidget(self.progress_bar)

        return layout

    def _init_logging(self) -> None:
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        if not any(
            isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout
            for handler in root_logger.handlers
        ):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
            )
            root_logger.addHandler(console_handler)

    def _load_default_config(self) -> None:
        config_path = Path("gui_config.json")
        if config_path.exists():
            self._load_config_from_file(config_path)

    def _browse_script(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择录制脚本",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self.script_path_edit.setText(file_path)

    def _get_current_config(self) -> Dict[str, Any]:
        return {
            "script_path": self.script_path_edit.text(),
            "browser": self.browser_combo.currentText(),
            "on_error": self.on_error_combo.currentText(),
            "log_level": self.log_level_combo.currentText(),
            "headless": self.headless_check.isChecked(),
            "wait_for_enter": self.wait_enter_check.isChecked(),
            "use_step_url": self.use_step_url_check.isChecked(),
            "auto_wait_video_after_click": self.auto_wait_video_check.isChecked(),
            "slow_mo": self.slow_mo_spin.value(),
            "video_start_timeout": self.video_start_spin.value(),
            "video_end_timeout": self.video_end_spin.value(),
        }

    def _apply_config(self, config: Dict[str, Any]) -> None:
        self.script_path_edit.setText(config.get("script_path", ""))
        self.browser_combo.setCurrentText(config.get("browser", "edge"))
        self.on_error_combo.setCurrentText(config.get("on_error", "stop"))
        self.log_level_combo.setCurrentText(config.get("log_level", "INFO"))
        self.headless_check.setChecked(config.get("headless", False))
        self.wait_enter_check.setChecked(config.get("wait_for_enter", True))
        self.use_step_url_check.setChecked(config.get("use_step_url", False))
        self.auto_wait_video_check.setChecked(
            config.get("auto_wait_video_after_click", True)
        )
        self.slow_mo_spin.setValue(config.get("slow_mo", 0))
        self.video_start_spin.setValue(config.get("video_start_timeout", 8))
        self.video_end_spin.setValue(config.get("video_end_timeout", 7200))

    def _save_config(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存配置",
            "gui_config.json",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            try:
                config = self._get_current_config()
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                logging.info(f"配置已保存: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存配置时出错: {e}")

    def _load_config(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载配置",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if file_path:
            self._load_config_from_file(file_path)

    def _load_config_from_file(self, file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self._apply_config(config)
            logging.info(f"配置已加载: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "加载失败", f"加载配置时出错: {e}")

    def _save_log(self) -> None:
        import time
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存日志",
            f"playback_log_{timestamp}.txt",
            "Text Files (*.txt);;All Files (*)",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.log_text.toPlainText())
                logging.info(f"日志已保存: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存日志时出错: {e}")

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        if not config["script_path"]:
            QMessageBox.warning(self, "配置错误", "请选择录制脚本 JSON 文件")
            return False

        script_path = Path(config["script_path"])
        if not script_path.exists():
            QMessageBox.warning(self, "配置错误", f"脚本文件不存在: {config['script_path']}")
            return False

        return True

    def _start_playback(self) -> None:
        config = self._get_current_config()

        if not self._validate_config(config):
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.continue_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("运行中...")
        self.log_text.clear()
        self.worker = WorkerThread(config)
        self.worker.log_signal.connect(self._append_log)
        self.worker.finished_signal.connect(self._on_playback_finished)
        self.worker.login_ready_signal.connect(self._on_login_ready)
        self.worker.start()

        self._append_log("=" * 50)
        self._append_log("开始回放任务")
        self._append_log(f"脚本: {config['script_path']}")
        self._append_log(f"浏览器: {config['browser']}")
        self._append_log("=" * 50)

    def _stop_playback(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.quit()
            if not self.worker.wait(3000):
                self.worker.terminate()
                self.worker.wait(1000)
            self._append_log("回放已停止")

        self._reset_ui_state()

    def _reset_ui_state(self) -> None:
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.continue_btn.setEnabled(False)
        self.progress_bar.setFormat("就绪")
        self.progress_bar.setValue(0)

    @Slot()
    def _on_login_ready(self) -> None:
        self.continue_btn.setEnabled(True)
        self.progress_bar.setFormat("等待登录完成...")
        self._append_log("请在浏览器中完成登录，然后点击“登录完成，开始回放”")

    def _continue_after_login(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.continue_after_login()
            self.continue_btn.setEnabled(False)
            self.progress_bar.setFormat("运行中...")

    @Slot(str)
    def _append_log(self, message: str) -> None:
        self.log_text.appendPlainText(message)

    @Slot(bool, str)
    def _on_playback_finished(self, success: bool, message: str) -> None:
        self._reset_ui_state()

        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", f"回放失败: {message}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("网课学习助手")
    app.setApplicationVersion("1.0.0")

    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
