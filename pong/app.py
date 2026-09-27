"""Command-line entry point: wires keyboard input, the CPU and the renderer
to a :class:`~pong.game.Game` and runs the turtle event loop."""

from __future__ import annotations

import argparse
import random
import time
import turtle
from collections.abc import Sequence
from tkinter import TclError

from pong.ai import CpuController
from pong.config import GameConfig
from pong.game import Game, Side
from pong.renderer import TurtleRenderer

# Physics runs at a fixed rate regardless of how often turtle manages to
# redraw, so ball speed and collisions behave the same on slow machines.
PHYSICS_STEP = 1 / 120
FRAME_MS = 16
# If the window stalls (e.g. while being dragged) don't try to catch up on
# seconds of missed simulation in one go.
MAX_FRAME_TIME = 0.25

# key name -> (side, direction). Both cases are bound so Caps Lock is harmless.
LEFT_KEYS = {"w": 1, "W": 1, "s": -1, "S": -1}
RIGHT_KEYS = {"Up": 1, "Down": -1}


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(prog="pong", description="Classic Pong built with turtle.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--cpu",
        action="store_true",
        help="single-player: you play the left paddle against the computer",
    )
    mode.add_argument(
        "--demo",
        action="store_true",
        help="watch the computer play itself",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=GameConfig().target_score,
        metavar="N",
        help="points needed to win (default: %(default)s)",
    )
    parser.add_argument(
        "--cpu-effort",
        type=float,
        default=CpuController().max_effort,
        metavar="F",
        help="CPU paddle speed as a fraction of a human's, 0-1 (default: %(default)s)",
    )
    parser.add_argument("--seed", type=int, default=None, help="seed for serve angles")
    parser.add_argument(
        "--quit-after",
        type=float,
        default=None,
        metavar="SECONDS",
        help="close the window automatically (useful for smoke tests)",
    )
    return parser


def key_bindings(single_player: bool) -> dict[str, tuple[Side, int]]:
    """Map key names to the paddle and direction they control.

    In single-player mode the arrow keys also drive the left paddle so either
    hand position works.
    """
    bindings = {key: (Side.LEFT, d) for key, d in LEFT_KEYS.items()}
    right_side = Side.LEFT if single_player else Side.RIGHT
    bindings.update({key: (right_side, d) for key, d in RIGHT_KEYS.items()})
    return bindings


class PongApp:
    """Runs one window's worth of Pong."""

    def __init__(self, args: argparse.Namespace) -> None:
        config = GameConfig(target_score=args.target)
        self.game = Game(config, rng=random.Random(args.seed))

        self.cpus: list[CpuController] = []
        if args.demo:
            self.cpus = [CpuController(side, args.cpu_effort) for side in Side]
            names = {Side.LEFT: "CPU 1", Side.RIGHT: "CPU 2"}
            hint = "P pause   R restart   Esc quit"
            self.bindings: dict[str, tuple[Side, int]] = {}
        elif args.cpu:
            self.cpus = [CpuController(Side.RIGHT, args.cpu_effort)]
            names = {Side.LEFT: "You", Side.RIGHT: "CPU"}
            hint = "W/S or Up/Down move   P pause   R restart   Esc quit"
            self.bindings = key_bindings(single_player=True)
        else:
            names = {Side.LEFT: "Player 1", Side.RIGHT: "Player 2"}
            hint = "P1: W/S   P2: Up/Down   P pause   R restart   Esc quit"
            self.bindings = key_bindings(single_player=False)

        self.screen = turtle.Screen()
        self.renderer = TurtleRenderer(self.screen, config, names, hint)
        self._held: set[str] = set()
        self._accumulator = 0.0
        self._last_time = time.perf_counter()
        self._running = True
        self._bind_keys()
        if args.quit_after is not None:
            self.screen.ontimer(self.quit, int(args.quit_after * 1000))

    # ----------------------------------------------------------------- input

    def _bind_keys(self) -> None:
        for key in self.bindings:
            self.screen.onkeypress(lambda k=key: self._on_press(k), key)
            self.screen.onkeyrelease(lambda k=key: self._on_release(k), key)
        for key in ("p", "P", "space"):
            self.screen.onkeypress(self.game.toggle_pause, key)
        for key in ("r", "R"):
            self.screen.onkeypress(self._restart, key)
        for key in ("Escape", "q", "Q"):
            self.screen.onkeypress(self.quit, key)
        self.screen.listen()

    def _on_press(self, key: str) -> None:
        self._held.add(key)
        self._refresh_directions()

    def _on_release(self, key: str) -> None:
        self._held.discard(key)
        self._refresh_directions()

    def _refresh_directions(self) -> None:
        # Recompute from every held key rather than the one just changed, so
        # releasing "up" while still holding "down" keeps the paddle moving.
        totals = {side: 0 for side in Side}
        for key in self._held:
            side, direction = self.bindings[key]
            totals[side] += direction
        for side, total in totals.items():
            if not any(cpu.side is side for cpu in self.cpus):
                self.game.set_direction(side, total)

    def _restart(self) -> None:
        self.game.restart()
        self._refresh_directions()

    # ------------------------------------------------------------------ loop

    def run(self) -> None:
        """Start the frame loop and hand control to tkinter."""
        self._tick()
        try:
            self.screen.mainloop()
        except (turtle.Terminator, TclError):
            pass

    def quit(self) -> None:
        """Close the window and stop the loop."""
        if not self._running:
            return
        self._running = False
        try:
            self.screen.bye()
        except (turtle.Terminator, TclError):
            pass

    def _tick(self) -> None:
        if not self._running:
            return
        now = time.perf_counter()
        self._accumulator += min(now - self._last_time, MAX_FRAME_TIME)
        self._last_time = now
        while self._accumulator >= PHYSICS_STEP:
            for cpu in self.cpus:
                cpu.apply(self.game, PHYSICS_STEP)
            self.game.update(PHYSICS_STEP)
            self._accumulator -= PHYSICS_STEP
        try:
            self.renderer.draw(self.game)
            self.screen.update()
            self.screen.ontimer(self._tick, FRAME_MS)
        except (turtle.Terminator, TclError):
            # The window was closed between frames.
            self._running = False


def main(argv: Sequence[str] | None = None) -> None:
    """Parse arguments and play."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.target < 1:
        parser.error("--target must be at least 1")
    if not 0 < args.cpu_effort <= 1:
        parser.error("--cpu-effort must be greater than 0 and at most 1")
    PongApp(args).run()
