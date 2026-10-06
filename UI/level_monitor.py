import math
from array import array

from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource


class LevelMonitor(QObject):
    """Reads a microphone and reports its loudness (0..1 on a -60..0 dB scale)."""

    level = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = None
        self._stream = None

    def start(self, device: QAudioDevice):
        self.stop()
        audio_format = QAudioFormat()
        audio_format.setSampleRate(16000)
        audio_format.setChannelCount(1)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(audio_format):
            audio_format = device.preferredFormat()

        self._source = QAudioSource(device, audio_format, self)
        self._stream = self._source.start()
        if self._stream is not None:
            self._stream.readyRead.connect(self._read)

    def stop(self):
        if self._source is not None:
            self._source.stop()
            self._source.deleteLater()
        self._source = None
        self._stream = None
        self.level.emit(0.0)

    def _read(self):
        if self._stream is None:
            return
        data = bytes(self._stream.readAll())
        sample_format = self._source.format().sampleFormat()

        if sample_format == QAudioFormat.SampleFormat.Float:
            samples = array("f", data[: len(data) // 4 * 4])
            peak = max((abs(s) for s in samples), default=0.0)
        elif sample_format == QAudioFormat.SampleFormat.Int16:
            samples = array("h", data[: len(data) // 2 * 2])
            peak = max((abs(s) for s in samples), default=0) / 32768
        else:
            return

        db = 20 * math.log10(peak) if peak > 0 else -60
        self.level.emit(max(0.0, min(1.0, (db + 60) / 60)))
