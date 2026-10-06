from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from UI.level_monitor import LevelMonitor
from UI.widgets import IconSquare, LevelBars

INPUT_DEVICE_KEY = "audio/input_device"


def _settings() -> QSettings:
    return QSettings("LectureAI", "LectureAI")


def _saved_device_id() -> str:
    return _settings().value(INPUT_DEVICE_KEY, "")


def _find_device(device_id: str):
    for device in QMediaDevices.audioInputs():
        if bytes(device.id()).hex() == device_id:
            return device
    return None


def saved_input_device() -> QAudioDevice:
    """The microphone chosen in Settings, or the system default if it's unavailable."""
    return _find_device(_saved_device_id()) or QMediaDevices.defaultAudioInput()


def input_device_description() -> str:
    device = _find_device(_saved_device_id())
    if device is not None:
        return device.description()
    default = QMediaDevices.defaultAudioInput().description()
    return f"padrão do sistema ({default})" if default else "nenhum encontrado"


class SettingsPage(QWidget):
    input_device_changed = Signal()

    def __init__(self):
        super().__init__()
        self.media_devices = QMediaDevices(self)
        self.level_monitor = LevelMonitor(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 34, 42, 40)
        layout.setSpacing(0)

        title = QLabel("Configurações")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addSpacing(4)
        subtitle = QLabel("Preferências deste computador")
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet("font-size: 15px;")
        layout.addWidget(subtitle)
        layout.addSpacing(26)

        card = QFrame()
        card.setObjectName("card")
        card.setMaximumWidth(640)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 22)
        card_layout.setSpacing(14)

        heading = QHBoxLayout()
        heading.setSpacing(12)
        heading.addWidget(IconSquare("mic"))
        texts = QVBoxLayout()
        texts.setSpacing(2)
        card_title = QLabel("Microfone")
        card_title.setObjectName("cardTitle")
        texts.addWidget(card_title)
        card_hint = QLabel("Usado nas novas gravações.")
        card_hint.setObjectName("faint")
        texts.addWidget(card_hint)
        heading.addLayout(texts, stretch=1)
        card_layout.addLayout(heading)

        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self._on_device_selected)
        card_layout.addWidget(self.device_combo)

        level_row = QHBoxLayout()
        level_row.setSpacing(12)
        self.level_bars = LevelBars(bars=24)
        level_row.addWidget(self.level_bars)
        level_hint = QLabel("Fale algo: as barras devem acender. Se ficarem apagadas, escolha outro microfone.")
        level_hint.setObjectName("faint")
        level_hint.setWordWrap(True)
        level_row.addWidget(level_hint, stretch=1)
        card_layout.addLayout(level_row)

        layout.addWidget(card)
        layout.addStretch()

        self.level_monitor.level.connect(self.level_bars.set_level)
        self.media_devices.audioInputsChanged.connect(self._load_devices)
        self._load_devices()

    def _load_devices(self):
        default = QMediaDevices.defaultAudioInput()

        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItem(f"Padrão do sistema ({default.description()})", "")
        for device in QMediaDevices.audioInputs():
            self.device_combo.addItem(device.description(), bytes(device.id()).hex())
        index = self.device_combo.findData(_saved_device_id())
        self.device_combo.setCurrentIndex(max(index, 0))
        self.device_combo.blockSignals(False)

        self.input_device_changed.emit()
        self._restart_meter()

    def _on_device_selected(self, _index):
        _settings().setValue(INPUT_DEVICE_KEY, self.device_combo.currentData())
        self.input_device_changed.emit()
        self._restart_meter()

    # The meter only listens while the page is visible

    def showEvent(self, event):
        super().showEvent(event)
        self._restart_meter()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.level_monitor.stop()

    def _restart_meter(self):
        if self.isVisible():
            self.level_monitor.start(saved_input_device())
        else:
            self.level_monitor.stop()
