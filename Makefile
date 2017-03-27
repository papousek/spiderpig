upload: register
	python setup.py sdist upload

register:
	python setup.py register

reinstall: check uninstall install

install: check
	python setup.py clean sdist
	pip install dist/spiderpig-*

uninstall:
	pip uninstall --yes spiderpig

check:
	flake8 --ignore=E501,E225,E123,E128,W503,E731 spiderpig

develop:
	python setup.py develop

test:
	pytest
