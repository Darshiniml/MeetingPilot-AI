"""Background service that captures selected audio into temporary WAV chunks."""

from queue import Empty, Queue
from threading import Event, Lock, Thread

from app.audio.buffer import AudioChunk, AudioChunkBuffer, TemporaryWavChunkWriter
from app.audio.capture import AudioCapture, AudioCaptureConfig
from app.audio.devices import AudioDevice, AudioDeviceManager, AudioSource


class AudioService:
    """Coordinate device selection, live capture, chunking, and safe shutdown."""

    def __init__(
        self,
        device_manager: AudioDeviceManager | None = None,
        capture_config: AudioCaptureConfig | None = None,
    ) -> None:
        """Create an idle audio service with injectable device infrastructure."""
        self._device_manager = device_manager or AudioDeviceManager()
        self._capture_config = capture_config or AudioCaptureConfig()
        self._capture: AudioCapture | None = None
        self._source: AudioSource | None = None
        self._worker: Thread | None = None
        self._stop_event = Event()
        self._lock = Lock()
        self._chunks: Queue[AudioChunk] = Queue()
        self._errors: Queue[Exception] = Queue()

    def list_microphones(self) -> list[AudioDevice]:
        """Return selectable physical microphone inputs."""
        return self._device_manager.list_microphones()

    def list_speakers(self) -> list[AudioDevice]:
        """Return selectable speaker outputs for user-facing device selection."""
        return self._device_manager.list_speakers()

    def list_system_audio_inputs(self) -> list[AudioDevice]:
        """Return selectable WASAPI loopback inputs for system-audio capture."""
        return self._device_manager.list_system_audio_inputs()

    def start_recording(self, source: AudioSource, device_identifier: str | None = None) -> None:
        """Start capturing the selected microphone or loopback input."""
        with self._lock:
            if self.is_recording:
                raise RuntimeError("Audio recording is already running")
            device = self._device_manager.select_input(source, device_identifier)
            self._capture = AudioCapture(device, self._capture_config)
            self._source = source
            self._capture.start()
            self._stop_event.clear()
            self._worker = Thread(target=self._capture_loop, name="audio-capture", daemon=True)
            self._worker.start()

    def stop_recording(self) -> list[AudioChunk]:
        """Stop capture, flush pending samples, and return all completed chunks."""
        with self._lock:
            worker = self._worker
            if worker is None:
                return self.drain_chunks()
            self._stop_event.set()
        worker.join(timeout=5)
        if worker.is_alive():
            raise RuntimeError("Audio capture did not stop within five seconds")
        with self._lock:
            self._worker = None
            self._capture = None
            self._source = None
        return self.drain_chunks()

    @property
    def is_recording(self) -> bool:
        """Return whether a capture worker is currently active."""
        return self._worker is not None and self._worker.is_alive()

    def drain_chunks(self) -> list[AudioChunk]:
        """Return and remove every WAV chunk completed since the last read."""
        chunks: list[AudioChunk] = []
        while True:
            try:
                chunks.append(self._chunks.get_nowait())
            except Empty:
                return chunks

    def raise_if_failed(self) -> None:
        """Raise the first capture error observed by the worker, if any."""
        try:
            error = self._errors.get_nowait()
        except Empty:
            return
        raise error

    def _capture_loop(self) -> None:
        """Read responsive frames and emit WAV chunks every ten seconds."""
        capture = self._capture
        if capture is None:
            return
        buffer = AudioChunkBuffer(
            sample_rate=self._capture_config.sample_rate,
            channels=self._capture_config.channels,
        )
        writer = TemporaryWavChunkWriter()
        try:
            while not self._stop_event.is_set():
                for samples in buffer.append(capture.read_frame()):
                    self._chunks.put(
                        writer.write(
                            samples,
                            source=self._selected_source(),
                            sample_rate=self._capture_config.sample_rate,
                        )
                    )
            remaining_samples = buffer.drain()
            if remaining_samples is not None:
                self._chunks.put(
                    writer.write(
                        remaining_samples,
                        source=self._selected_source(),
                        sample_rate=self._capture_config.sample_rate,
                    )
                )
        except Exception as error:
            self._errors.put(error)
        finally:
            capture.stop()

    def _selected_source(self) -> AudioSource:
        """Return the active source for chunk metadata."""
        if self._source is None:
            raise RuntimeError("No active audio source is configured")
        return self._source
