from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QWidget

from UI.icons import icon


def _format_ms(ms: int) -> str:
    seconds = ms // 1000
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class AudioPlayer(QWidget):
    """Small play/pause bar for listening back to a lecture's audio."""

    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.play_button = QPushButton()
        self.play_button.setFixedSize(32, 32)
        self.play_button.setIconSize(QSize(14, 14))
        self.play_button.setStyleSheet("border-radius: 16px; padding: 0;")
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.clicked.connect(self._toggle)
        layout.addWidget(self.play_button)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.sliderMoved.connect(self.player.setPosition)
        layout.addWidget(self.slider, stretch=1)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("faint")
        layout.addWidget(self.time_label)

        self.player.durationChanged.connect(self._on_duration)
        self.player.positionChanged.connect(self._on_position)
        self.player.playbackStateChanged.connect(self._on_state)
        self._on_state(QMediaPlayer.PlaybackState.StoppedState)

    def load(self, path: str):
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(path) if path else QUrl())

    def stop(self):
        self.player.stop()

    def _toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_duration(self, duration):
        self.slider.setRange(0, duration)
        self._on_position(self.player.position())

    def _on_position(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.time_label.setText(f"{_format_ms(position)} / {_format_ms(self.player.duration())}")

    def _on_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_button.setIcon(icon("pause" if playing else "play", "white", 14))
