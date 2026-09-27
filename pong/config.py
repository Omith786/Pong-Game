"""Tunable constants for the court, paddles and ball.

Everything is expressed in turtle's coordinate system: the origin sits at the
centre of the window, x grows to the right and y grows upwards. Speeds are in
pixels per second so the physics is independent of the frame rate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GameConfig:
    """Immutable game settings shared by the logic, the CPU and the renderer."""

    width: int = 800
    height: int = 600

    paddle_width: float = 20.0
    paddle_height: float = 100.0
    # Distance from the side wall to the centre of each paddle.
    paddle_inset: float = 50.0
    paddle_speed: float = 420.0

    ball_radius: float = 10.0
    ball_start_speed: float = 320.0
    # Multiplier applied on every paddle hit, capped so the swept collision
    # check and the players both keep up.
    ball_speedup: float = 1.06
    ball_max_speed: float = 950.0

    # Hitting the very tip of a paddle deflects the ball by this much.
    max_bounce_angle_deg: float = 60.0
    # Serves are kept fairly flat so the receiver has a fair chance.
    max_serve_angle_deg: float = 25.0
    serve_delay: float = 1.0

    target_score: int = 7

    def __post_init__(self) -> None:
        if self.target_score < 1:
            raise ValueError("target_score must be at least 1")
        if not 0 < self.max_bounce_angle_deg < 90:
            raise ValueError("max_bounce_angle_deg must be between 0 and 90")
        if self.paddle_height >= self.height:
            raise ValueError("paddle_height must be smaller than the court height")

    @property
    def half_width(self) -> float:
        return self.width / 2

    @property
    def half_height(self) -> float:
        return self.height / 2

    @property
    def paddle_x(self) -> float:
        """Absolute x position of the paddle centres (left is negative)."""
        return self.half_width - self.paddle_inset

    @property
    def max_bounce_angle(self) -> float:
        return math.radians(self.max_bounce_angle_deg)

    @property
    def max_serve_angle(self) -> float:
        return math.radians(self.max_serve_angle_deg)
