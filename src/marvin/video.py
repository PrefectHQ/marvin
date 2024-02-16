"""Utilities for working with video."""

import queue
import threading
import time
from typing import Optional

from marvin.types import Image
from marvin.utilities.logging import get_logger

try:
    import cv2
except ImportError:
    raise ImportError(
        'Marvin was not installed with the "video" extra. Please run `pip install'
        ' "marvin[video]"` to use this module.'
    )


logger = get_logger(__name__)


class BackgroundVideoRecorder:
    def __init__(self, resolution: Optional[tuple[int, int]] = None):
        if resolution is None:
            resolution = (150, 200)
        self.resolution = resolution
        self.is_recording = False
        self.queue = queue.Queue()
        self._stop_event = None
        self._thread = None

    def __len__(self) -> int:
        return self.queue.qsize()

    def __iter__(self) -> "BackgroundVideoRecorder":
        return self

    def __next__(self) -> Image:
        while True:
            if not self.is_recording and self.queue.empty():
                raise StopIteration
            try:
                return self.queue.get(timeout=0.25)
            except queue.Empty:
                continue

    def _record_thread(self, device: int, interval_seconds: int):
        camera = cv2.VideoCapture(device)

        if not camera.isOpened():
            logger.error("Camera not found.")
            return

        try:
            while not self._stop_event.is_set():
                ret, frame = camera.read()
                if ret:
                    if self.resolution is not None:
                        frame = cv2.resize(frame, self.resolution)
                    _, frame_bytes = cv2.imencode(".png", frame)
                    image = Image(data=frame_bytes.tobytes(), format="png")
                    self.queue.put(image)
                time.sleep(interval_seconds)
        finally:
            camera.release()

    def start_recording(
        self, device: int = 0, interval_seconds: int = 2, clear_queue: bool = False
    ):
        if self.is_recording:
            raise ValueError("Recording is already in progress.")
        if clear_queue:
            self.queue.queue.clear()
        self.is_recording = True
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._record_thread,
            args=(device, interval_seconds),
        )
        self._thread.daemon = True
        self._thread.start()
        logger.info("Video recording started.")

    def stop_recording(self, wait: bool = True):
        if not self.is_recording:
            raise ValueError("Recording is not in progress.")
        self._stop_event.set()
        if wait:
            self._thread.join()
        self.is_recording = False
        logger.info("Video recording finished.")


def record_background(
    device: int = 0, interval_seconds: int = 2
) -> BackgroundVideoRecorder:
    recorder = BackgroundVideoRecorder()
    recorder.start_recording(device, interval_seconds)
    return recorder
