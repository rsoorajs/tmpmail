.PHONY: test
test:
	python -m pytest --black --flake8 --mypy --isort
