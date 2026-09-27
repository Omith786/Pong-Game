"""A deliberately simple CPU opponent.

The CPU follows the ball's current height while it is approaching and drifts
back to the middle while it is moving away. It never predicts bounces and moves
slower than a human-controlled paddle, so steep returns off the paddle tips
are the way to beat it.
"""

from __future__ import annotations

from dataclasses import dataclass

from pong.game import Game, Phase, Side


@dataclass
class CpuController:
    """Steers one paddle towards the ball.

    ``max_effort`` scales the paddle's top speed (1.0 matches a human player);
    ``tolerance`` is how far off-centre the ball may be before the CPU bothers
    to move, which stops it twitching on every tiny change.
    """

    side: Side = Side.RIGHT
    max_effort: float = 0.75
    tolerance: float = 8.0

    def __post_init__(self) -> None:
        if not 0 < self.max_effort <= 1:
            raise ValueError("max_effort must be in (0, 1]")

    def target_y(self, game: Game) -> float:
        """The height the paddle is currently trying to reach."""
        ball = game.ball
        approaching = game.phase is Phase.PLAYING and ball.vx * self.side.sign > 0
        return ball.y if approaching else 0.0

    def decide(self, game: Game, dt: float) -> float:
        """Return a paddle direction in ``[-max_effort, max_effort]``."""
        if dt <= 0:
            return 0.0
        paddle = game.paddle(self.side)
        error = self.target_y(game) - paddle.y
        if abs(error) <= self.tolerance:
            return 0.0
        # Scale by how far the paddle could travel this step so it slows down
        # as it arrives instead of overshooting and oscillating.
        full_step = game.config.paddle_speed * dt
        direction = error / full_step
        return max(-self.max_effort, min(self.max_effort, direction))

    def apply(self, game: Game, dt: float) -> None:
        """Decide and push the result straight into the game."""
        game.set_direction(self.side, self.decide(game, dt))
