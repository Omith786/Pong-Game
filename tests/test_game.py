import math
import random

import pytest

from pong.config import GameConfig
from pong.game import Ball, Game, Phase, Side

STEP = 1 / 120


def playing_game(config: GameConfig | None = None, **ball: float) -> Game:
    """A game already past the serve, with the ball placed as requested."""
    game = Game(config or GameConfig(), rng=random.Random(0))
    game.phase = Phase.PLAYING
    game.ball = Ball(**ball)
    return game


def test_config_rejects_nonsense() -> None:
    with pytest.raises(ValueError):
        GameConfig(target_score=0)
    with pytest.raises(ValueError):
        GameConfig(max_bounce_angle_deg=90)


def test_new_game_starts_serving_at_nil_nil() -> None:
    game = Game(rng=random.Random(1))
    assert game.phase is Phase.SERVING
    assert game.scores == {Side.LEFT: 0, Side.RIGHT: 0}
    assert (game.ball.x, game.ball.y, game.ball.speed) == (0, 0, 0)


class TestPaddles:
    def test_moves_at_configured_speed(self) -> None:
        game = playing_game(vx=0.0)
        game.set_direction(Side.LEFT, 1)
        game.update(0.1)
        assert game.left.y == pytest.approx(game.config.paddle_speed * 0.1)

    def test_direction_is_clamped(self) -> None:
        game = playing_game()
        game.set_direction(Side.RIGHT, -5)
        assert game.right.direction == -1

    def test_stays_inside_court(self) -> None:
        game = playing_game()
        game.set_direction(Side.LEFT, 1)
        game.set_direction(Side.RIGHT, -1)
        game.update(10)
        limit = game.config.half_height - game.config.paddle_height / 2
        assert game.left.y == pytest.approx(limit)
        assert game.right.y == pytest.approx(-limit)

    def test_can_move_while_waiting_for_serve(self) -> None:
        game = Game(rng=random.Random(0))
        game.set_direction(Side.LEFT, -1)
        game.update(0.1)
        assert game.left.y < 0


class TestWalls:
    def test_bounces_off_top_wall(self) -> None:
        cfg = GameConfig()
        top = cfg.half_height - cfg.ball_radius
        game = playing_game(y=top - 1, vy=300.0)
        game.update(STEP)
        assert game.ball.vy < 0
        assert game.ball.y <= top

    def test_bounces_off_bottom_wall(self) -> None:
        cfg = GameConfig()
        bottom = -(cfg.half_height - cfg.ball_radius)
        game = playing_game(y=bottom + 1, vy=-300.0)
        game.update(STEP)
        assert game.ball.vy > 0
        assert game.ball.y >= bottom


class TestPaddleHits:
    def _ball_about_to_hit_right(self, game: Game, offset: float, speed: float = 400.0) -> None:
        cfg = game.config
        face = cfg.paddle_x - cfg.paddle_width / 2
        game.ball = Ball(x=face - cfg.ball_radius - 1, y=game.right.y + offset, vx=speed)

    def test_reverses_and_speeds_up(self) -> None:
        game = playing_game()
        self._ball_about_to_hit_right(game, offset=0)
        game.update(STEP)
        assert game.ball.vx < 0
        assert game.ball.speed == pytest.approx(400 * game.config.ball_speedup)
        assert game.rally_hits == 1

    def test_centre_hit_returns_flat(self) -> None:
        game = playing_game()
        self._ball_about_to_hit_right(game, offset=0)
        game.update(STEP)
        assert game.ball.vy == pytest.approx(0)

    def test_hit_position_sets_angle(self) -> None:
        cfg = GameConfig()
        angles = {}
        for offset in (-45, -20, 20, 45):
            game = playing_game(cfg)
            self._ball_about_to_hit_right(game, offset=offset)
            game.update(STEP)
            angles[offset] = math.atan2(game.ball.vy, -game.ball.vx)
        # Above centre deflects upwards, below deflects downwards, and hits
        # further from the centre come off steeper.
        assert angles[20] > 0 > angles[-20]
        assert angles[45] > angles[20]
        assert angles[-45] < angles[-20]
        assert abs(angles[45]) <= cfg.max_bounce_angle

    def test_tip_hit_uses_max_angle(self) -> None:
        cfg = GameConfig()
        game = playing_game(cfg)
        reach = cfg.paddle_height / 2 + cfg.ball_radius
        self._ball_about_to_hit_right(game, offset=reach)
        game.update(STEP)
        angle = math.atan2(game.ball.vy, -game.ball.vx)
        assert angle == pytest.approx(cfg.max_bounce_angle, abs=1e-6)

    def test_speed_is_capped(self) -> None:
        game = playing_game()
        self._ball_about_to_hit_right(game, offset=0, speed=game.config.ball_max_speed)
        game.update(STEP)
        assert game.ball.speed == pytest.approx(game.config.ball_max_speed)

    def test_left_paddle_hit(self) -> None:
        cfg = GameConfig()
        game = playing_game(cfg)
        face = -cfg.paddle_x + cfg.paddle_width / 2
        game.ball = Ball(x=face + cfg.ball_radius + 1, y=0, vx=-400)
        game.update(STEP)
        assert game.ball.vx > 0

    def test_ball_cannot_tunnel_through_paddle(self) -> None:
        # One huge step would carry the ball far past the paddle; the swept
        # check must still catch the crossing.
        game = playing_game(x=0.0, y=0.0, vx=900.0)
        game.update(1.0)
        assert game.ball.vx < 0
        assert game.scores[Side.LEFT] == 0

    def test_miss_when_paddle_out_of_reach(self) -> None:
        game = playing_game()
        self._ball_about_to_hit_right(game, offset=game.config.paddle_height)
        game.update(STEP)
        assert game.ball.vx > 0


class TestScoring:
    def test_ball_past_right_edge_scores_for_left(self) -> None:
        cfg = GameConfig()
        game = playing_game(cfg, x=cfg.half_width, y=cfg.half_height - 20, vx=500.0)
        game.update(0.1)
        assert game.scores == {Side.LEFT: 1, Side.RIGHT: 0}
        assert game.phase is Phase.SERVING
        assert game.serve_towards is Side.RIGHT
        assert (game.ball.x, game.ball.y) == (0, 0)

    def test_ball_past_left_edge_scores_for_right(self) -> None:
        cfg = GameConfig()
        game = playing_game(cfg, x=-cfg.half_width, y=cfg.half_height - 20, vx=-500.0)
        game.update(0.1)
        assert game.scores[Side.RIGHT] == 1
        assert game.serve_towards is Side.LEFT

    def test_serve_launches_after_delay(self) -> None:
        cfg = GameConfig()
        game = Game(cfg, rng=random.Random(3))
        game.serve_towards = Side.LEFT
        game.update(cfg.serve_delay / 2)
        assert game.phase is Phase.SERVING
        game.update(cfg.serve_delay)
        assert game.phase is Phase.PLAYING
        assert game.ball.vx < 0
        assert game.ball.speed == pytest.approx(cfg.ball_start_speed)
        angle = abs(math.atan2(game.ball.vy, -game.ball.vx))
        assert angle <= cfg.max_serve_angle

    def test_first_to_target_wins(self) -> None:
        cfg = GameConfig(target_score=2)
        game = playing_game(cfg)
        game.scores[Side.RIGHT] = 1
        game.ball = Ball(x=-cfg.half_width, y=cfg.half_height - 20, vx=-500)
        game.update(0.1)
        assert game.phase is Phase.GAME_OVER
        assert game.winner is Side.RIGHT

    def test_nothing_moves_after_game_over(self) -> None:
        game = playing_game()
        game.phase = Phase.GAME_OVER
        game.set_direction(Side.LEFT, 1)
        game.update(1)
        assert game.left.y == 0


class TestPauseAndRestart:
    def test_pause_freezes_everything(self) -> None:
        game = playing_game(vx=300.0, vy=100.0)
        game.set_direction(Side.LEFT, 1)
        game.toggle_pause()
        game.update(0.5)
        assert (game.ball.x, game.ball.y, game.left.y) == (0, 0, 0)
        game.toggle_pause()
        game.update(0.1)
        assert game.ball.x > 0

    def test_cannot_pause_finished_game(self) -> None:
        game = playing_game()
        game.phase = Phase.GAME_OVER
        game.toggle_pause()
        assert not game.paused

    def test_restart_resets_match(self) -> None:
        game = playing_game(vx=300.0)
        game.scores[Side.LEFT] = 5
        game.left.y = 100
        game.paused = True
        game.restart()
        assert game.scores == {Side.LEFT: 0, Side.RIGHT: 0}
        assert game.phase is Phase.SERVING
        assert not game.paused
        assert game.left.y == 0
        assert game.ball.speed == 0
