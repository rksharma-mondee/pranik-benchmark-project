.PHONY: setup test lint format eval clean

setup:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

test:
	python -m pytest

lint:
	ruff check .
	mypy .

format:
	ruff format .
	ruff check --fix .

eval:
	python evaluation/pipelines/batch_eval.py --config configs/app/dev.yaml

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"

