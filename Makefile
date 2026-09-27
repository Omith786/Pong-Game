PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: venv install run cpu demo test clean

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(BIN)/pip install -r requirements.txt

run:
	$(BIN)/python -m pong

cpu:
	$(BIN)/python -m pong --cpu

demo:
	$(BIN)/python -m pong --demo

test:
	$(BIN)/python -m pytest -q

clean:
	find . -path ./$(VENV) -prune -o -name __pycache__ -type d -exec rm -rf {} +
	rm -rf .pytest_cache
