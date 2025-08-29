lint:
	ruff check --select E,F,W,B,C4,I --ignore E402,E501,E712,B904,B905 --exclude=CTFd/uploads CTFd/ migrations/ tests/
	npm run lint
	black --check --diff --exclude=CTFd/uploads --exclude=node_modules .
	prettier --check 'CTFd/themes/**/assets/**/*'
	prettier --check '**/*.md'

format:
	isort --skip=CTFd/uploads -rc CTFd/ tests/
	black --exclude=CTFd/uploads --exclude=node_modules .
	prettier --write 'CTFd/themes/**/assets/**/*'
	prettier --write '**/*.md'

test:
	pytest -rf --cov=CTFd --cov-context=test --cov-report=xml \
		--ignore-glob="**/node_modules/" \
		--ignore=node_modules/ \
		-W ignore::sqlalchemy.exc.SADeprecationWarning \
		-W ignore::sqlalchemy.exc.SAWarning \
		-n auto
	bandit -r CTFd -x CTFd/uploads --skip B105,B322
	pipdeptree
	npm run verify

test-fast:
	@echo "Running optimized test suite with parallel execution..."
	pytest -n auto --dist=loadfile \
		--tb=short \
		--durations=10 \
		--maxfail=5 \
		-rf \
		--ignore-glob="**/node_modules/" \
		--ignore=node_modules/ \
		-W ignore::sqlalchemy.exc.SADeprecationWarning \
		-W ignore::sqlalchemy.exc.SAWarning \
		tests/

test-unit:
	@echo "Running unit tests only (fast)..."
	pytest -n auto --dist=loadfile \
		-m "unit and not slow" \
		--tb=short \
		--durations=5 \
		tests/

test-integration:
	@echo "Running integration tests..."
	pytest -n auto --dist=loadfile \
		-m integration \
		--tb=short \
		--durations=10 \
		tests/

test-slow:
	@echo "Running slow tests (legacy create_ctfd pattern)..."
	pytest -n auto --dist=loadfile \
		-m slow \
		--tb=short \
		--durations=20 \
		tests/

test-optimized:
	@echo "Running optimized tests only (using fixtures)..."
	pytest -n auto --dist=loadfile \
		--tb=short \
		--durations=5 \
		tests/api/v1/test_challenges_optimized.py \
		tests/conftest.py

test-performance:
	@echo "Running performance comparison..."
	@echo "=== Legacy Test Performance ==="
	time pytest tests/test_setup.py::test_setup_integrations -v
	@echo "=== Optimized Test Performance ==="  
	time pytest tests/api/v1/test_challenges_optimized.py::TestChallengesVisibility::test_api_challenges_visibility -v

test-coverage:
	pytest --cov=CTFd --cov-context=test --cov-report=html --cov-report=xml \
		-n auto --dist=loadfile \
		--ignore-glob="**/node_modules/" \
		--ignore=node_modules/ \
		-W ignore::sqlalchemy.exc.SADeprecationWarning \
		-W ignore::sqlalchemy.exc.SAWarning \
		tests/

coverage:
	coverage html --show-contexts

serve:
	python serve.py

shell:
	python manage.py shell

translations-init:
	# make translations-init lang=af
	pybabel init -i messages.pot -d CTFd/translations -l $(lang)

translations-extract:
	pybabel extract -F babel.cfg -k lazy_gettext -k _l -o messages.pot .

translations-update:
	pybabel update --ignore-obsolete -i messages.pot -d CTFd/translations

translations-compile:
	pybabel compile -f -d CTFd/translations

translations-lint:
	dennis-cmd lint CTFd/translations
