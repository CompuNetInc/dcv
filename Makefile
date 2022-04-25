lint:
	python -m isort .
	python -m black .
	python -m pylama .
	python -m pydocstyle .
	python -m mypy --strict --no-warn-return-any dcv/

.PHONY: build
build:
	docker build -f Dockerfile -t dcv:latest .
