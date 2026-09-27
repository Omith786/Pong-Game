"""Draws a :class:`~pong.game.Game` with the standard-library turtle module.

The renderer is read-only with respect to the game: it copies positions onto
turtles each frame and redraws text only when it actually changes, because
``Turtle.write`` is comparatively slow and rewriting it every frame flickers.
"""

from __future__ import annotations

import turtle

from pong.config import GameConfig
from pong.game import Game, Phase, Side

# Turtle's built-in "square" and "circle" shapes are 20 x 20 pixels at scale 1.
_SHAPE_SIZE = 20
_FONT = "Courier"
_FOREGROUND = "white"
_BACKGROUND = "black"
_DIM = "gray50"


def _make_writer() -> turtle.Turtle:
    pen = turtle.Turtle(visible=False)
    pen.penup()
    pen.speed(0)
    return pen


class TurtleRenderer:
    """Owns the turtles that make up the court and keeps them in sync."""

    def __init__(
        self,
        screen: turtle._Screen,
        config: GameConfig,
        names: dict[Side, str],
        controls_hint: str,
    ) -> None:
        self.screen = screen
        self.config = config
        self.names = names

        screen.title("Pong")
        screen.bgcolor(_BACKGROUND)
        screen.setup(width=config.width, height=config.height)
        # Manual refresh: we call screen.update() once per frame ourselves.
        screen.tracer(0)

        self._draw_centre_line()
        self._draw_hint(controls_hint)

        self._paddles = {side: self._make_paddle() for side in Side}
        self._ball = self._make_ball()
        self._score_pen = _make_writer()
        self._message_pen = _make_writer()
        self._last_score: str | None = None
        self._last_message: str | None = None

    # ----------------------------------------------------------------- set-up

    def _make_paddle(self) -> turtle.Turtle:
        paddle = turtle.Turtle(shape="square")
        paddle.color(_FOREGROUND)
        paddle.penup()
        paddle.speed(0)
        paddle.shapesize(
            stretch_wid=self.config.paddle_height / _SHAPE_SIZE,
            stretch_len=self.config.paddle_width / _SHAPE_SIZE,
        )
        return paddle

    def _make_ball(self) -> turtle.Turtle:
        ball = turtle.Turtle(shape="circle")
        ball.color(_FOREGROUND)
        ball.penup()
        ball.speed(0)
        scale = 2 * self.config.ball_radius / _SHAPE_SIZE
        ball.shapesize(stretch_wid=scale, stretch_len=scale)
        return ball

    def _draw_centre_line(self) -> None:
        pen = _make_writer()
        pen.color(_DIM)
        pen.pensize(3)
        pen.setheading(270)
        pen.goto(0, self.config.half_height)
        dash = 20
        for _ in range(int(self.config.height // (2 * dash)) + 1):
            pen.pendown()
            pen.forward(dash)
            pen.penup()
            pen.forward(dash)

    def _draw_hint(self, text: str) -> None:
        pen = _make_writer()
        pen.color(_DIM)
        pen.goto(0, -self.config.half_height + 15)
        pen.write(text, align="center", font=(_FONT, 12, "normal"))

    # ------------------------------------------------------------------ frame

    def draw(self, game: Game) -> None:
        """Copy the current game state onto the screen (without refreshing)."""
        for side, pen in self._paddles.items():
            paddle = game.paddle(side)
            pen.goto(paddle.x, paddle.y)

        if game.phase is Phase.GAME_OVER:
            self._ball.hideturtle()
        else:
            self._ball.showturtle()
            self._ball.goto(game.ball.x, game.ball.y)

        self._write_score(game)
        self._write_message(game)

    def _write_score(self, game: Game) -> None:
        left, right = game.scores[Side.LEFT], game.scores[Side.RIGHT]
        text = f"{left}     {right}"
        if text == self._last_score:
            return
        self._last_score = text
        pen = self._score_pen
        pen.clear()
        pen.color(_FOREGROUND)
        pen.goto(0, self.config.half_height - 70)
        pen.write(text, align="center", font=(_FONT, 40, "bold"))

    def _write_message(self, game: Game) -> None:
        text = banner_text(game, self.names)
        if text == self._last_message:
            return
        self._last_message = text
        pen = self._message_pen
        pen.clear()
        if text:
            pen.color(_FOREGROUND)
            pen.goto(0, 60)
            pen.write(text, align="center", font=(_FONT, 20, "normal"))


def banner_text(game: Game, names: dict[Side, str]) -> str:
    """The banner shown over the court (empty during normal play)."""
    if game.phase is Phase.GAME_OVER and game.winner is not None:
        return f"{names[game.winner]} wins!\nPress R to play again"
    if game.paused:
        return "Paused\nPress P to resume"
    return ""
