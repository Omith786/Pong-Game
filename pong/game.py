"""Pure game state and physics for Pong.

Nothing in this module touches turtle or tkinter, so the whole rule set can be
exercised by unit tests without a display. The renderer only ever reads from a
:class:`Game`; input handlers only ever call its public methods.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

from pong.config import GameConfig


class Side(Enum):
    """A player's side of the court."""

    LEFT = -1
    RIGHT = 1

    @property
    def sign(self) -> int:
        """-1 for the left side, +1 for the right; handy for x maths."""
        return self.value

    @property
    def opponent(self) -> Side:
        return Side.RIGHT if self is Side.LEFT else Side.LEFT


class Phase(Enum):
    """What the match is currently doing."""

    SERVING = "serving"
    PLAYING = "playing"
    GAME_OVER = "game_over"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class Paddle:
    """A vertical paddle that moves along a fixed x position."""

    side: Side
    x: float
    y: float = 0.0
    # Desired movement in [-1, 1]; keyboard input uses -1/0/1 while the CPU
    # uses fractional values to glide onto its target without jittering.
    direction: float = 0.0


@dataclass
class Ball:
    """The ball's position and velocity (pixels and pixels per second)."""

    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)


class Game:
    """A single match of Pong, advanced in discrete time steps.

    The ball is swept along its path each step rather than only checked at its
    end position, so it cannot tunnel through a paddle even when it is moving
    fast or the step is large.
    """

    def __init__(self, config: GameConfig | None = None, rng: random.Random | None = None) -> None:
        self.config = config or GameConfig()
        self._rng = rng or random.Random()
        self._reset()

    def _reset(self) -> None:
        self.left = Paddle(Side.LEFT, -self.config.paddle_x)
        self.right = Paddle(Side.RIGHT, self.config.paddle_x)
        self.ball = Ball()
        self.scores: dict[Side, int] = {Side.LEFT: 0, Side.RIGHT: 0}
        self.phase = Phase.SERVING
        self.paused = False
        self.winner: Side | None = None
        self.rally_hits = 0
        self.serve_towards = self._rng.choice([Side.LEFT, Side.RIGHT])
        self.serve_timer = self.config.serve_delay

    # ------------------------------------------------------------------ input

    def paddle(self, side: Side) -> Paddle:
        """Return the paddle belonging to ``side``."""
        return self.left if side is Side.LEFT else self.right

    def set_direction(self, side: Side, direction: float) -> None:
        """Set how a paddle should move: -1 is down, +1 is up, 0 is still."""
        self.paddle(side).direction = _clamp(direction, -1.0, 1.0)

    def toggle_pause(self) -> None:
        """Pause or resume play. Has no effect once the match is decided."""
        if self.phase is not Phase.GAME_OVER:
            self.paused = not self.paused

    def restart(self) -> None:
        """Reset scores, paddles and the ball for a fresh match."""
        self._reset()

    # ---------------------------------------------------------------- physics

    def update(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds."""
        if dt <= 0 or self.paused or self.phase is Phase.GAME_OVER:
            return

        self._move_paddles(dt)

        if self.phase is Phase.SERVING:
            self.serve_timer -= dt
            if self.serve_timer <= 0:
                self._launch_ball()
            return

        self._move_ball(dt)

    def _move_paddles(self, dt: float) -> None:
        limit = self.config.half_height - self.config.paddle_height / 2
        for paddle in (self.left, self.right):
            paddle.y += paddle.direction * self.config.paddle_speed * dt
            paddle.y = _clamp(paddle.y, -limit, limit)

    def _launch_ball(self) -> None:
        cfg = self.config
        angle = self._rng.uniform(-cfg.max_serve_angle, cfg.max_serve_angle)
        sign = self.serve_towards.sign
        self.ball = Ball(
            x=0.0,
            y=0.0,
            vx=sign * cfg.ball_start_speed * math.cos(angle),
            vy=cfg.ball_start_speed * math.sin(angle),
        )
        self.rally_hits = 0
        self.phase = Phase.PLAYING

    def _move_ball(self, dt: float) -> None:
        cfg = self.config
        ball = self.ball
        prev_x, prev_y = ball.x, ball.y
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt

        # Reflect off the top and bottom walls, mirroring any overshoot so the
        # ball does not lose distance on a bounce.
        top = cfg.half_height - cfg.ball_radius
        if ball.y > top:
            ball.y = 2 * top - ball.y
            ball.vy = -abs(ball.vy)
        elif ball.y < -top:
            ball.y = -2 * top - ball.y
            ball.vy = abs(ball.vy)

        target = self.right if ball.vx > 0 else self.left
        if self._check_paddle_hit(target, prev_x, prev_y):
            return

        if ball.x - cfg.ball_radius > cfg.half_width:
            self._award_point(Side.LEFT)
        elif ball.x + cfg.ball_radius < -cfg.half_width:
            self._award_point(Side.RIGHT)

    def _check_paddle_hit(self, paddle: Paddle, prev_x: float, prev_y: float) -> bool:
        """Bounce the ball off ``paddle`` if its path crossed the paddle face."""
        cfg = self.config
        ball = self.ball
        sign = paddle.side.sign
        # The face is the edge of the paddle pointing at the centre line; the
        # leading edge is the side of the ball travelling towards it.
        face_x = paddle.x - sign * cfg.paddle_width / 2
        prev_lead = prev_x + sign * cfg.ball_radius
        new_lead = ball.x + sign * cfg.ball_radius

        was_before = (face_x - prev_lead) * sign >= 0
        is_past = (new_lead - face_x) * sign >= 0
        if not (was_before and is_past):
            return False

        travelled = new_lead - prev_lead
        t = (face_x - prev_lead) / travelled if travelled else 0.0
        y_at_face = prev_y + (ball.y - prev_y) * t

        reach = cfg.paddle_height / 2 + cfg.ball_radius
        offset = y_at_face - paddle.y
        if abs(offset) > reach:
            return False

        # Where the ball meets the paddle sets the outgoing angle: dead centre
        # returns it flat, the tips send it away steeply.
        angle = (offset / reach) * cfg.max_bounce_angle
        speed = min(ball.speed * cfg.ball_speedup, cfg.ball_max_speed)
        ball.vx = -sign * speed * math.cos(angle)
        ball.vy = speed * math.sin(angle)
        ball.x = face_x - sign * cfg.ball_radius
        ball.y = y_at_face
        self.rally_hits += 1
        return True

    def _award_point(self, scorer: Side) -> None:
        self.scores[scorer] += 1
        if self.scores[scorer] >= self.config.target_score:
            self.winner = scorer
            self.phase = Phase.GAME_OVER
            self.ball = Ball()
            return
        # The player who conceded receives the next serve.
        self.serve_towards = scorer.opponent
        self.ball = Ball()
        self.phase = Phase.SERVING
        self.serve_timer = self.config.serve_delay
