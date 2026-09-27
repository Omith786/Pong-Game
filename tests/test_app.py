"""Checks for the turtle-facing modules that do not need a window."""

import random

import pytest

pytest.importorskip("tkinter", reason="tkinter is not installed")

import turtle  # noqa: E402

from pong.app import build_parser, key_bindings  # noqa: E402
from pong.game import Game, Phase, Side  # noqa: E402
from pong.renderer import TurtleRenderer, banner_text  # noqa: E402

NAMES = {Side.LEFT: "Player 1", Side.RIGHT: "Player 2"}


def test_turtle_imports() -> None:
    assert hasattr(turtle, "Screen")
    assert TurtleRenderer is not None


def test_parser_defaults_to_two_players() -> None:
    args = build_parser().parse_args([])
    assert not args.cpu and not args.demo
    assert args.target == 7


def test_parser_modes_are_exclusive() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--cpu", "--demo"])


def test_parser_options() -> None:
    args = build_parser().parse_args(["--cpu", "--target", "3", "--cpu-effort", "0.5"])
    assert args.cpu and args.target == 3 and args.cpu_effort == 0.5


def test_two_player_bindings_split_between_paddles() -> None:
    bindings = key_bindings(single_player=False)
    assert bindings["w"] == (Side.LEFT, 1)
    assert bindings["Down"] == (Side.RIGHT, -1)


def test_single_player_arrows_drive_left_paddle() -> None:
    bindings = key_bindings(single_player=True)
    assert {side for side, _ in bindings.values()} == {Side.LEFT}


def test_banner_text() -> None:
    game = Game(rng=random.Random(0))
    assert banner_text(game, NAMES) == ""
    game.toggle_pause()
    assert "Paused" in banner_text(game, NAMES)
    game.phase, game.winner = Phase.GAME_OVER, Side.RIGHT
    assert banner_text(game, NAMES).startswith("Player 2 wins!")


@pytest.mark.parametrize("argv", [["--target", "0"], ["--cpu-effort", "1.5"], ["--cpu-effort", "0"]])
def test_main_rejects_bad_options_before_opening_a_window(argv: list[str]) -> None:
    from pong.app import main

    with pytest.raises(SystemExit):
        main(argv)
