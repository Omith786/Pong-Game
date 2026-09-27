import random

import pytest

from pong.ai import CpuController
from pong.config import GameConfig
from pong.game import Ball, Game, Phase, Side

STEP = 1 / 120


def game_with_ball(**ball: float) -> Game:
    game = Game(rng=random.Random(0))
    game.phase = Phase.PLAYING
    game.ball = Ball(**ball)
    return game


def test_rejects_invalid_effort() -> None:
    with pytest.raises(ValueError):
        CpuController(max_effort=0)
    with pytest.raises(ValueError):
        CpuController(max_effort=1.5)


def test_tracks_approaching_ball() -> None:
    cpu = CpuController(Side.RIGHT, max_effort=0.8)
    game = game_with_ball(y=150, vx=300)
    assert cpu.decide(game, STEP) == pytest.approx(0.8)
    game.ball.y = -150
    assert cpu.decide(game, STEP) == pytest.approx(-0.8)


def test_returns_to_centre_when_ball_moves_away() -> None:
    cpu = CpuController(Side.RIGHT)
    game = game_with_ball(y=150, vx=-300)
    game.right.y = 120
    assert cpu.target_y(game) == 0
    assert cpu.decide(game, STEP) < 0


def test_left_side_cpu_tracks_leftward_ball() -> None:
    cpu = CpuController(Side.LEFT)
    game = game_with_ball(y=100, vx=-300)
    assert cpu.target_y(game) == 100


def test_holds_still_within_tolerance() -> None:
    cpu = CpuController(Side.RIGHT, tolerance=10)
    game = game_with_ball(y=5, vx=300)
    assert cpu.decide(game, STEP) == 0


def test_settles_on_target_without_overshoot() -> None:
    cpu = CpuController(Side.RIGHT, tolerance=0.5)
    game = game_with_ball(y=137, vx=1e-9)
    for _ in range(240):
        cpu.apply(game, STEP)
        game._move_paddles(STEP)
        assert game.right.y <= 137 + 1e-9
    assert game.right.y == pytest.approx(137, abs=1)


def test_returns_a_straight_ball() -> None:
    cfg = GameConfig()
    cpu = CpuController(Side.RIGHT)
    game = Game(cfg, rng=random.Random(0))
    game.phase = Phase.PLAYING
    game.ball = Ball(x=0, y=80, vx=cfg.ball_start_speed)
    for _ in range(240):
        cpu.apply(game, STEP)
        game.update(STEP)
        if game.ball.vx < 0:
            break
    assert game.ball.vx < 0
    assert game.scores[Side.LEFT] == 0


def test_cpu_versus_cpu_match_finishes() -> None:
    # Two CPUs chasing fading returns should still produce a result, and the
    # simulation must stay stable for a whole match.
    cfg = GameConfig(target_score=3)
    game = Game(cfg, rng=random.Random(42))
    cpus = [CpuController(side, max_effort=0.6) for side in Side]
    for _ in range(120 * 60 * 10):
        for cpu in cpus:
            cpu.apply(game, STEP)
        game.update(STEP)
        assert abs(game.ball.y) <= cfg.half_height
        if game.phase is Phase.GAME_OVER:
            break
    assert game.phase is Phase.GAME_OVER
    assert max(game.scores.values()) == 3
