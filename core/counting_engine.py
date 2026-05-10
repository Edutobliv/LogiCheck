from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


CATEGORIES = ("Cemento", "Tubería Presión", "Tubería Sanitaria")


@dataclass(frozen=True)
class DetectionBox:
    x1: int
    y1: int
    x2: int
    y2: int
    track_id: Optional[int | str]
    category: str

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


@dataclass(frozen=True)
class CountingEvent:
    frame_idx: int
    category: str
    direction: str
    track_id: int | str
    delta: int
    count_after: int


@dataclass
class _TrackState:
    x: float
    y: float
    frame_idx: int
    category: str
    seen_frames: int = 1


class CountingEngine:
    """
    Counts objects crossing a horizontal line using track ids when available
    and a small proximity tracker as fallback.
    """

    def __init__(
        self,
        categories: Iterable[str] = CATEGORIES,
        stale_frames: int = 15,
        proxy_match_px: float = 70.0,
        min_seen_frames: int = 1,
    ):
        self.categories = tuple(categories)
        self.stale_frames = stale_frames
        self.proxy_match_px = proxy_match_px
        self.min_seen_frames = max(1, min_seen_frames)
        self.reset()

    def reset(self):
        self.counts = {cat: 0 for cat in self.categories}
        self._prev_positions: dict[int | str, _TrackState] = {}
        self._counted_directions: dict[int | str, str] = {}
        self._proxy_seq = 0

    def process(
        self,
        boxes: Iterable[DetectionBox],
        frame_idx: int,
        line_y: float,
    ) -> list[CountingEvent]:
        self._drop_stale(frame_idx)
        events: list[CountingEvent] = []

        for box in boxes:
            if box.category not in self.counts:
                continue

            cx, cy = box.center
            track_key = self._resolve_track_key(box.track_id, cx, cy)
            prev = self._prev_positions.get(track_key)

            if prev is not None and prev.seen_frames >= self.min_seen_frames:
                delta, direction = self._crossing_delta(prev.y, cy, line_y, track_key)
                if delta:
                    self.counts[box.category] = max(0, self.counts[box.category] + delta)
                    events.append(
                        CountingEvent(
                            frame_idx=frame_idx,
                            category=box.category,
                            direction=direction,
                            track_id=track_key,
                            delta=delta,
                            count_after=self.counts[box.category],
                        )
                    )

            seen_frames = (prev.seen_frames + 1) if prev else 1
            self._prev_positions[track_key] = _TrackState(
                x=cx,
                y=cy,
                frame_idx=frame_idx,
                category=box.category,
                seen_frames=seen_frames,
            )

        return events

    def _drop_stale(self, frame_idx: int):
        stale = [
            key for key, state in self._prev_positions.items()
            if frame_idx - state.frame_idx >= self.stale_frames
        ]
        for key in stale:
            self._prev_positions.pop(key, None)
            self._counted_directions.pop(key, None)

    def _resolve_track_key(
        self,
        track_id: Optional[int | str],
        cx: float,
        cy: float,
    ) -> int | str:
        if track_id is not None:
            return track_id

        best_key = None
        best_dist = self.proxy_match_px
        for key, state in self._prev_positions.items():
            if not isinstance(key, str) or not key.startswith("proxy_"):
                continue
            dx = cx - state.x
            dy = cy - state.y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < best_dist:
                best_key = key
                best_dist = dist

        if best_key is not None:
            return best_key

        self._proxy_seq += 1
        return f"proxy_{self._proxy_seq}"

    def _crossing_delta(
        self,
        prev_y: float,
        curr_y: float,
        line_y: float,
        track_key: int | str,
    ) -> tuple[int, str]:
        crossed_down = prev_y < line_y <= curr_y
        crossed_up = prev_y >= line_y > curr_y

        if not crossed_down and not crossed_up:
            return 0, ""

        crossing_direction = "down" if crossed_down else "up"
        counted_direction = self._counted_directions.get(track_key)

        if counted_direction is None:
            self._counted_directions[track_key] = crossing_direction
            return 1, "despachado"

        if counted_direction != crossing_direction:
            self._counted_directions.pop(track_key, None)
            return -1, "retornado"

        return 0, ""


def map_model_class_to_category(class_name: str) -> Optional[str]:
    normalized = (
        class_name.lower()
        .replace("í", "i")
        .replace("ó", "o")
        .replace("á", "a")
        .replace("é", "e")
        .replace("ú", "u")
    )

    if normalized in {"bulto", "cemento", "bag"}:
        return "Cemento"
    if "tuberia" in normalized and "presion" in normalized:
        return "Tubería Presión"
    if "tuberia" in normalized and "sanitaria" in normalized:
        return "Tubería Sanitaria"
    return None
