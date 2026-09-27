# Pong-Game

The classic Pong game, programmed with Python's built-in `turtle` library. I originally wrote it to improve my Python skills and learn how the turtle library works; this version keeps turtle for all of the drawing but separates the game rules from the rendering, so the physics can be unit tested without opening a window. Two people can play on one keyboard, or one person can play against a simple computer-controlled paddle.

## Features

- Two-player mode on a single keyboard (W/S and the arrow keys)
- Single-player mode against a CPU paddle, with adjustable CPU speed
- Demo mode where the computer plays itself
- Live score display and a first-to-N win condition (7 by default)
- Pause/resume and restart at any time
- The ball speeds up a little on every paddle hit, up to a cap
- The return angle depends on where the ball meets the paddle: the centre sends it back flat, the tips send it away steeply
- Fixed-rate physics with swept collision detection, so the ball cannot pass through a paddle at high speed
- No third-party runtime dependencies: only the Python standard library

## Controls

| Key | Two-player | Single-player (`--cpu`) |
| --- | --- | --- |
| `W` / `S` | Left paddle up / down | Your paddle up / down |
| `Up` / `Down` | Right paddle up / down | Your paddle up / down |
| `P` or `Space` | Pause / resume | Pause / resume |
| `R` | Restart the match | Restart the match |
| `Esc` or `Q` | Quit | Quit |

## Project structure

```
Pong-Game/
├── pong/
│   ├── config.py     # GameConfig: court size, speeds, angles, target score
│   ├── game.py       # Game state and physics (no turtle imports)
│   ├── ai.py         # CpuController: the computer opponent
│   ├── renderer.py   # TurtleRenderer: draws a Game with turtle
│   ├── app.py        # CLI, keyboard bindings and the frame loop
│   └── __main__.py   # enables `python -m pong`
├── tests/
│   ├── test_game.py  # paddles, walls, bounce angles, scoring, pause/restart
│   ├── test_ai.py    # CPU behaviour, including a full CPU vs CPU match
│   └── test_app.py   # CLI parsing, key bindings, banner text, turtle import
├── Makefile
├── pyproject.toml
└── requirements.txt
```

### How it fits together

- **`game.py`** holds everything that decides what happens: paddle and ball positions, wall bounces, paddle collisions, scoring, serving, pausing and the win condition. `Game.update(dt)` advances the match by `dt` seconds. It never imports turtle, which is what makes it testable.
- **`ai.py`** looks at a `Game` and chooses a direction for one paddle. It follows the ball's current height while the ball is coming towards it and drifts back to the middle otherwise. It does not predict wall bounces and moves slower than a human paddle, so it can be beaten by aiming off the paddle tips.
- **`renderer.py`** only reads from the `Game`. It moves the paddle and ball turtles each frame and rewrites the score and banner text only when they change, because `Turtle.write` is slow and flickers if called every frame.
- **`app.py`** binds keys to the game and runs the loop. Rendering happens roughly every 16 ms via `screen.ontimer`, while the physics is stepped at a fixed 120 Hz using an accumulator. That keeps the ball speed and collisions consistent even if turtle cannot redraw at a steady rate.

### Physics notes

- **Bounce angle.** The offset between the ball and the paddle centre, divided by the paddle's reach (half its height plus the ball radius), is mapped linearly onto `[-60°, +60°]`.
- **Speed-up.** Each hit multiplies the speed by 1.06, capped at 950 px/s.
- **Tunnelling.** Rather than only checking whether the ball overlaps a paddle at the end of a step, the game checks whether the ball's leading edge crossed the paddle face during the step and interpolates the height at which it did.
- **Serving.** After each point the ball waits in the centre for one second, then is served towards the player who conceded, at a random angle of up to 25°.

All of these values live in `GameConfig` and can be changed in one place.

## Tech stack

- Python 3.10+ (developed and tested on Python 3.14)
- `turtle` and `tkinter` from the standard library for graphics and input
- `pytest` for the test suite

## Getting started

`turtle` depends on tkinter. It is included with the python.org installers for macOS and Windows. On other setups you may need to install it separately:

- Homebrew Python: `brew install python-tk`
- Debian/Ubuntu: `sudo apt install python3-tk`

Then clone the repository and set up a virtual environment (only needed for the tests, since the game itself has no dependencies):

```bash
git clone https://github.com/Omith786/Pong-Game.git
cd Pong-Game
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or use the Makefile:

```bash
make install
```

## Usage

```bash
python -m pong                 # two players
python -m pong --cpu           # play against the computer
python -m pong --demo          # watch the computer play itself
python -m pong --target 3      # first to 3 points wins
python -m pong --cpu --cpu-effort 0.9   # a faster, harder CPU (0 to 1)
```

The Makefile has shortcuts: `make run`, `make cpu` and `make demo`. Installing the package (`pip install -e .`) also adds a `pong` command.

Other options:

- `--seed N` makes serve angles repeatable
- `--quit-after SECONDS` closes the window automatically, which is handy for a quick check that the game starts

## Testing

```bash
make test
# or
python -m pytest -q
```

The tests cover the game logic and the CPU without creating a window, so they run on machines with no display. `tests/test_app.py` also checks the command-line parsing, key bindings and banner text; it imports turtle but never opens a screen, and it is skipped if tkinter is not installed.

## Possible future work

- Sound effects on hits and points (turtle has no audio, so this would need a small platform-specific helper)
- A CPU that predicts where the ball will land, with difficulty levels that add reaction delay or aiming error
- Spin: let the paddle's own movement influence the return angle
- A start menu for choosing the mode and target score in the window instead of on the command line
- Remappable keys
