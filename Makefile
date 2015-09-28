.PHONY = init clean test run

.DEFAULT_GOAL = run

venv ?= .env
venv_python ?= python3
bin = $(venv)/bin

init:
	@if [ -d "$(venv)" ]; then echo "virtualenv $(venv) exists"; exit 1; fi
	@virtualenv -p $(venv_python) $(venv)
	@$(bin)/pip install -e git+https://github.com/PSU-OIT-ARC/arctasks#egg=psu.oit.arc.tasks
	@$(bin)/inv init --overwrite

clean:
	@$(bin)/inv clean

test:
	@$(bin)/inv test

run:
	@$(bin)/inv runserver

to ?= stage
deploy:
	$(bin)/inv configure --env $(to) deploy
