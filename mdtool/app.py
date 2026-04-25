"""PyQt6 desktop UI: convert files to markdown, edit, preview, and chunk."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .chunker import byte_len, chunk_markdown
from .converters import convert_file, supported_extensions


def _mono_font() -> QFont:
    f = QFont()
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setFamily("Menlo")
    return f


class ChunkCard(QFrame):
    def __init__(self, index: int, total: int, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.addWidget(QLabel(f"<b>Chunk {index}/{total}</b>"))
        header.addWidget(QLabel(f"<span style='color:#666'>{byte_len(text)} bytes</span>"))
        header.addStretch()

        self._copy_btn = QPushButton("복사")
        self._copy_btn.setFixedWidth(80)
        self._copy_btn.clicked.connect(self._copy)
        header.addWidget(self._copy_btn)
        layout.addLayout(header)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(text)
        body.setFont(_mono_font())
        line_count = max(3, min(10, text.count("\n") + 2))
        body.setFixedHeight(22 * line_count)
        layout.addWidget(body)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._text)
        self._copy_btn.setText("복사됨")
        QTimer.singleShot(1200, lambda: self._copy_btn.setText("복사"))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("mdtool — 파일을 Markdown으로")
        self.resize(1100, 800)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(350)
        self._refresh_timer.timeout.connect(self._refresh)

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        top = QHBoxLayout()
        open_btn = QPushButton("파일 선택...")
        open_btn.clicked.connect(self._open_file)
        top.addWidget(open_btn)

        save_btn = QPushButton("Markdown 저장...")
        save_btn.clicked.connect(self._save_markdown)
        top.addWidget(save_btn)

        clear_btn = QPushButton("비우기")
        clear_btn.clicked.connect(lambda: self.editor.clear())
        top.addWidget(clear_btn)

        top.addSpacing(20)
        top.addWidget(QLabel("청크 최대 바이트:"))
        self.max_bytes = QSpinBox()
        self.max_bytes.setRange(100, 10000)
        self.max_bytes.setSingleStep(100)
        self.max_bytes.setValue(1000)
        self.max_bytes.valueChanged.connect(lambda _: self._refresh_timer.start())
        top.addWidget(self.max_bytes)

        top.addStretch()
        self.path_label = QLabel("")
        top.addWidget(self.path_label)
        outer.addLayout(top)

        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setFont(_mono_font())
        self.editor.setPlaceholderText(
            "여기에 markdown을 붙여넣거나 직접 작성하세요.\n"
            "또는 '파일 선택...'으로 .pptx 등을 변환하세요.\n"
            "내용이 바뀌면 미리보기와 청크가 자동 갱신됩니다."
        )
        self.editor.textChanged.connect(self._refresh_timer.start)
        self.tabs.addTab(self.editor, "편집")

        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.tabs.addTab(self.preview, "미리보기")

        self.chunk_scroll = QScrollArea()
        self.chunk_scroll.setWidgetResizable(True)
        self.chunk_container = QWidget()
        self.chunk_layout = QVBoxLayout(self.chunk_container)
        self.chunk_layout.setContentsMargins(6, 6, 6, 6)
        self.chunk_layout.setSpacing(8)
        self.chunk_layout.addStretch()
        self.chunk_scroll.setWidget(self.chunk_container)
        self.tabs.addTab(self.chunk_scroll, "청크")

    def _open_file(self) -> None:
        exts = " ".join(f"*{e}" for e in supported_extensions())
        filt = f"지원 파일 ({exts});;모든 파일 (*)"
        path, _ = QFileDialog.getOpenFileName(self, "변환할 파일 선택", "", filt)
        if not path:
            return
        try:
            md = convert_file(Path(path))
        except Exception as e:
            QMessageBox.critical(self, "변환 실패", f"{type(e).__name__}: {e}")
            return
        self.path_label.setText(Path(path).name)
        self.editor.setPlainText(md)
        self.tabs.setCurrentWidget(self.editor)

    def _save_markdown(self) -> None:
        text = self.editor.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "저장", "저장할 내용이 없습니다.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Markdown 저장", "", "Markdown (*.md);;모든 파일 (*)"
        )
        if not path:
            return
        Path(path).write_text(text, encoding="utf-8")

    def _refresh(self) -> None:
        text = self.editor.toPlainText()
        self.preview.setMarkdown(text)
        self._rebuild_chunks(text)

    def _rebuild_chunks(self, text: str) -> None:
        while self.chunk_layout.count() > 1:
            item = self.chunk_layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.deleteLater()

        chunks = chunk_markdown(text, max_bytes=self.max_bytes.value())
        if not chunks:
            placeholder = QLabel("청크할 내용이 없습니다.")
            placeholder.setStyleSheet("color:#888; padding:12px;")
            self.chunk_layout.insertWidget(0, placeholder)
            return

        for i, ch in enumerate(chunks, start=1):
            card = ChunkCard(i, len(chunks), ch)
            self.chunk_layout.insertWidget(self.chunk_layout.count() - 1, card)


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
