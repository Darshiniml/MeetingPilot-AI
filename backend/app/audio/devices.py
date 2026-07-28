"""Windows-capable microphone, speaker, and loopback device discovery."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import soundcard as sc


class AudioSource(str, Enum):
    """Supported audio sources for a capture session."""

    MICROPHONE = "microphone"
    SYSTEM_AUDIO = "system_audio"


@dataclass(frozen=True, slots=True)
class AudioDevice:
    """A selectable native audio endpoint exposed to the application."""

    identifier: str
    name: str
    source: AudioSource


class AudioDeviceManager:
    """Discover and select native recording devices through SoundCard/WASAPI."""

    def list_microphones(self) -> list[AudioDevice]:
        """Return physical microphone inputs, excluding speaker loopback devices."""
        return [
            self._to_device(device, AudioSource.MICROPHONE)
            for device in sc.all_microphones(include_loopback=False)
        ]

    def list_speakers(self) -> list[AudioDevice]:
        """Return speaker outputs that users may choose for loopback recording."""
        return [
            AudioDevice(
                identifier=str(device.name),
                name=str(device.name),
                source=AudioSource.SYSTEM_AUDIO,
            )
            for device in sc.all_speakers()
        ]

    def list_system_audio_inputs(self) -> list[AudioDevice]:
        """Return WASAPI loopback inputs representing speaker output streams."""
        return [
            self._to_device(device, AudioSource.SYSTEM_AUDIO)
            for device in sc.all_microphones(include_loopback=True)
            if getattr(device, "isloopback", False)
        ]

    def select_input(self, source: AudioSource, identifier: str | None) -> Any:
        """Return the native recording device selected for the requested source."""
        if source is AudioSource.MICROPHONE:
            return sc.default_microphone() if identifier is None else sc.get_microphone(identifier)

        loopback_devices = sc.all_microphones(include_loopback=True)
        for device in loopback_devices:
            if getattr(device, "isloopback", False) and (
                identifier is None or str(device.name) == identifier
            ):
                return device
        raise ValueError("A valid system-audio loopback device must be selected")

    @staticmethod
    def _to_device(device: Any, source: AudioSource) -> AudioDevice:
        """Convert a SoundCard device object into a stable application value."""
        return AudioDevice(
            identifier=str(device.name),
            name=str(device.name),
            source=source,
        )
