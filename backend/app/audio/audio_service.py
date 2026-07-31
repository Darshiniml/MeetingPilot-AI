"""Background service that captures selected audio into temporary WAV chunks."""

from queue import Empty, Queue
from threading import Event, Lock, Thread
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from app.audio.buffer import AudioChunk, AudioChunkBuffer, TemporaryWavChunkWriter
from app.audio.capture import AudioCapture, AudioCaptureConfig
from app.audio.devices import AudioDevice, AudioDeviceManager, AudioSource
import logging


logger = logging.getLogger(__name__)


class AudioService:
    """Coordinate device selection, live capture, chunking, and safe shutdown."""

    def __init__(
        self,
        device_manager: AudioDeviceManager | None = None,
        capture_config: AudioCaptureConfig | None = None,
        chunk_handler: Callable[[AudioChunk], None] | None = None,
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
        self._chunk_handler = chunk_handler
        self._handler_jobs: Queue[tuple[Callable[[AudioChunk], None], AudioChunk]] = Queue()
        self._handler_worker: Thread | None = None

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
            self._ensure_handler_worker()
            self._worker = Thread(target=self._capture_loop, name="audio-capture", daemon=True)
            self._worker.start()
            logger.info("Audio service started", extra={"source": source.value})

    def set_chunk_handler(self, chunk_handler: Callable[[AudioChunk], None] | None) -> None:
        """Set the processor for chunks from the next recording session."""
        with self._lock:
            if self.is_recording:
                raise RuntimeError("Cannot change the chunk handler while recording")
            self._chunk_handler = chunk_handler

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
        next_chunk_started_at = datetime.now(timezone.utc)
        frame_count = 0
        logger.info("Recording thread running")
        try:
            while not self._stop_event.is_set():
                frame = capture.read_frame()
                frame_count += 1
                if frame_count == 1:
                    logger.info("Audio frame received")
                for samples in buffer.append(frame):
                    chunk = writer.write(
                        samples,
                        source=self._selected_source(),
                        sample_rate=self._capture_config.sample_rate,
                        started_at=next_chunk_started_at,
                    )
                    next_chunk_started_at += timedelta(
                        seconds=chunk.frame_count / chunk.sample_rate
                    )
                    self._publish_chunk(chunk)
            remaining_samples = buffer.drain()
            if remaining_samples is not None:
                chunk = writer.write(
                    remaining_samples,
                    source=self._selected_source(),
                    sample_rate=self._capture_config.sample_rate,
                    started_at=next_chunk_started_at,
                )
                self._publish_chunk(chunk)
        except Exception as error:
            self._errors.put(error)
            logger.exception("Audio recording thread stopped due to an error")
        finally:
            capture.stop()

    def _publish_chunk(self, chunk: AudioChunk) -> None:
        """Queue a completed WAV chunk and dispatch it to an optional processor."""
        self._chunks.put(chunk)
        logger.info("WAV chunk created", extra={"path": str(chunk.path), "chunk_index": chunk.chunk_index})
        handler = self._chunk_handler
        if handler is None:
            return
        self._handler_jobs.put((handler, chunk))

    def _ensure_handler_worker(self) -> None:
        """Run slow chunk processing away from the time-sensitive recorder thread."""
        if self._handler_worker is not None and self._handler_worker.is_alive():
            return
        self._handler_worker = Thread(
            target=self._handle_chunks,
            name="audio-chunk-handler",
            daemon=True,
        )
        self._handler_worker.start()

    def _handle_chunks(self) -> None:
        """Process completed chunks serially without delaying capture shutdown."""
        while True:
            handler, chunk = self._handler_jobs.get()
            try:
                handler(chunk)
            except Exception as error:
                self._errors.put(error)
                logger.exception(
                    "Audio chunk handler failed",
                    extra={"path": str(chunk.path), "chunk_index": chunk.chunk_index},
                )
            finally:
                self._handler_jobs.task_done()

    def _selected_source(self) -> AudioSource:
        """Return the active source for chunk metadata."""
        if self._source is None:
            raise RuntimeError("No active audio source is configured")
        return self._source


_audio_service: AudioService | None = None
_audio_service_lock = Lock()


def get_audio_service() -> AudioService:
    """Return the one process-wide audio capture service."""
    global _audio_service
    with _audio_service_lock:
        if _audio_service is None:
            _audio_service = AudioService()
        return _audio_service
