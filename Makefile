# OSV-Scanner (https://google.github.io/osv-scanner/) checks every resolved Maven dependency.
OSV ?= osv-scanner

.PHONY: setup lint test vectors report experiments audit ci

setup:
	cd python && python -m pip install --upgrade pip && python -m pip install -e ".[dev]"

# Generated vectors up to date, then each language's static checks.
lint:
	python spec/generate_vectors.py --check
	cd java && mvn -B -q -DskipTests compile
	cd python && python -m ruff check . ../spec && python -m ruff format --check . ../spec && python -m mypy
	cd js && npm run -s lint

# Shared vectors, Money API cases and seeded random invariants in Java, Python and JavaScript.
test:
	cd java && mvn -B -q verify
	cd python && python -m pytest -q
	cd js && npm test

# Rebuild doubles.tsv, ops.tsv and sums.tsv from exact rational arithmetic.
vectors:
	python spec/generate_vectors.py

# passed / cases for each language on the shared vectors (tab-separated).
report:
	cd java && mvn -B -q -DskipTests compile && java -cp target/classes portfolio.floatingpointandmoney.App report
	cd python && python -m floating_point_and_money report
	cd js && node src/cli.js report

# The experiments: how 0.1 is stored, float operations next to Money, error growth in sums.
experiments:
	cd python && python -m floating_point_and_money explain 0.1
	cd python && python -m floating_point_and_money ops
	cd python && python -m floating_point_and_money sums

# Known vulnerabilities in Python, npm and Maven dependencies.
audit:
	cd python && python -m pip_audit --skip-editable --cache-dir ../.tmp/pip-audit
	cd js && npm audit
	cd java && mvn -B -q org.cyclonedx:cyclonedx-maven-plugin:2.9.3:makeAggregateBom -DoutputFormat=json -DoutputName=bom -DincludeTestScope=true
	$(OSV) scan source -L java/target/bom.json

ci: setup lint test report
