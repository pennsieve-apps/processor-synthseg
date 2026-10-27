.PHONY: help test run clean

SERVICE_NAME ?= processor-synthseg
export DOCKER_DEFAULT_PLATFORM = linux/amd64

.DEFAULT: help

help:
	@echo "Make Help for $(SERVICE_NAME)"
	@echo ""
	@echo "make test   - run the processor over data/input/ with the local Python (needs requirements.txt"
	@echo "              installed and FREESURFER_HOME pointing at a folder with vendor/synthseg + models)"
	@echo "make run    - build the image and run it over data/input/, writing to data/output/"
	@echo "make clean  - remove data/output/"

test: clean
	INPUT_DIR=data/input OUTPUT_DIR=data/output python3 -m processor.main
	@cat data/output/labels/provenance.json

run: clean
	docker compose -f docker-compose.yml down --remove-orphans
	docker compose -f docker-compose.yml build
	docker compose -f docker-compose.yml up --exit-code-from processor
	@find data/output -type f | sort

clean:
	rm -rf data/output
