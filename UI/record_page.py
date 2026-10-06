from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioInput, QMediaCaptureSession, QMediaFormat, QMediaRecorder
from PySide6.QtWidgets import QFileDialog, QLabel, QLineEdit, QMessageBox, QVBoxLayout, QWidget

from UI import styles
from UI.controller import RECORDINGS_DIR
from UI.level_monitor import LevelMonitor
from UI.settings_page import input_device_description, saved_input_device
from UI.widgets import DropZone, LevelBars, RecordButton

AUDIO_FILTER = "Áudio (*.m4a *.mp3 *.wav *.flac *.ogg *.aac *.mp4)"
COLUMN_WIDTH = 460


class RecordPage(QWidget):
    lecture_created = Signal(int)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._pending_title = None

        self.session = QMediaCaptureSession()
        self.audio_input = QAudioInput()
        self.session.setAudioInput(self.audio_input)
        self.recorder = QMediaRecorder()
        self.session.setRecorder(self.recorder)

        media_format = QMediaFormat()
        media_format.setFileFormat(QMediaFormat.FileFormat.Mpeg4Audio)
        media_format.setAudioCodec(QMediaFormat.AudioCodec.AAC)
        self.recorder.setMediaFormat(media_format)
        self.recorder.setQuality(QMediaRecorder.Quality.HighQuality)

        self.recorder.durationChanged.connect(self._update_timer)
        self.recorder.recorderStateChanged.connect(self._on_state_changed)
        self.recorder.errorOccurred.connect(self._on_error)

        # Live level while recording, so a silent microphone is noticed right away
        self.level_monitor = LevelMonitor(self)

        self._build_ui()
        self.level_monitor.level.connect(self.level_bars.set_level)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 30, 42, 40)
        layout.setSpacing(0)

        header = QLabel("Nova gravação")
        header.setObjectName("pageHeader")
        layout.addWidget(header)
        layout.addStretch(2)

        center = Qt.AlignmentFlag.AlignHCenter

        self.title_label = QLabel("Pronto para gravar")
        self.title_label.setObjectName("heroTitle")
        layout.addWidget(self.title_label, alignment=center)
        layout.addSpacing(8)
        self.subtitle_label = QLabel("A aula é transcrita no seu computador assim que você parar.")
        self.subtitle_label.setObjectName("muted")
        self.subtitle_label.setStyleSheet("font-size: 15px;")
        layout.addWidget(self.subtitle_label, alignment=center)
        layout.addSpacing(28)

        field = QWidget()
        field.setFixedWidth(COLUMN_WIDTH)
        field_layout = QVBoxLayout(field)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(8)
        name_label = QLabel(f'Nome da lecture <span style="color:{styles.TEXT_MUTED}; font-weight:400">(opcional)</span>')
        name_label.setObjectName("fieldLabel")
        field_layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: Ciência Política — Aula 7")
        field_layout.addWidget(self.name_input)
        layout.addWidget(field, alignment=center)
        layout.addSpacing(28)

        self.record_button = RecordButton()
        self.record_button.clicked.connect(self._toggle_recording)
        layout.addWidget(self.record_button, alignment=center)
        layout.addSpacing(26)

        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timer")
        layout.addWidget(self.timer_label, alignment=center)
        layout.addSpacing(14)

        self.level_bars = LevelBars()
        layout.addWidget(self.level_bars, alignment=center)
        layout.addSpacing(18)

        self.device_label = QLabel()
        self.device_label.setObjectName("muted")
        self.device_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.device_label, alignment=center)
        layout.addSpacing(28)

        self.drop_zone = DropZone()
        self.drop_zone.setFixedWidth(COLUMN_WIDTH)
        self.drop_zone.clicked.connect(self._import_file)
        self.drop_zone.file_dropped.connect(self._import_path)
        layout.addWidget(self.drop_zone, alignment=center)
        layout.addStretch(3)

        self.update_input_device()

    def update_input_device(self):
        if self.is_recording():
            return
        self.audio_input.setDevice(saved_input_device())
        self.device_label.setText(f"Microfone: {input_device_description()}")

    def is_recording(self) -> bool:
        return self.recorder.recorderState() != QMediaRecorder.RecorderState.StoppedState

    def stop(self):
        if self.is_recording():
            self.recorder.stop()

    def _toggle_recording(self):
        if self.is_recording():
            self.recorder.stop()
            return

        self.update_input_device()
        RECORDINGS_DIR.mkdir(exist_ok=True)
        now = datetime.now()
        self._pending_title = self.name_input.text().strip() or f"Lecture {now:%d/%m/%Y %H:%M}"
        path = RECORDINGS_DIR / f"{now:%Y-%m-%d_%H-%M-%S}.m4a"
        self.recorder.setOutputLocation(QUrl.fromLocalFile(str(path)))
        self.recorder.record()

    def _on_state_changed(self, state):
        recording = state != QMediaRecorder.RecorderState.StoppedState
        self.record_button.set_recording(recording)
        self.name_input.setEnabled(not recording)
        self.drop_zone.setEnabled(not recording)

        if recording:
            self.title_label.setText("Gravando")
            self.subtitle_label.setText("Clique no botão para parar e começar a transcrição.")
            self.level_monitor.start(saved_input_device())
            return

        self.level_monitor.stop()
        self.title_label.setText("Pronto para gravar")
        self.subtitle_label.setText("A aula é transcrita no seu computador assim que você parar.")

        # The file is only complete once the recorder reports it stopped
        location = self.recorder.actualLocation().toLocalFile()
        if self._pending_title and location and Path(location).exists():
            self._save_lecture(self._pending_title, Path(location))
        self._pending_title = None

    def _update_timer(self, ms):
        seconds = ms // 1000
        self.timer_label.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")

    def _on_error(self, _error, message):
        self._pending_title = None
        QMessageBox.warning(
            self, "Erro na gravação",
            f"{message}\n\nVerifique se o app tem permissão para usar o microfone em "
            "Ajustes do Sistema → Privacidade e Segurança → Microfone.",
        )

    def _import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Escolher áudio", str(Path.home()), AUDIO_FILTER)
        if path:
            self._import_path(Path(path))

    def _import_path(self, path: Path):
        self._save_lecture(self.name_input.text().strip() or path.stem, path)

    def _save_lecture(self, title: str, audio_path: Path):
        lecture_id = self.controller.add_lecture(title, audio_path)
        self.name_input.clear()
        self.timer_label.setText("00:00")
        self.lecture_created.emit(lecture_id)
