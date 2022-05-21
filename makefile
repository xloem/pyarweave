twine_upload: ensure-git clean sdist bdist_wheel twine_check

help:
	@echo 'Target name is simply passed to setup.py . make build, make install, make bdist_wheel ...'

%:
	python3 setup.py "$@"

ensure-git:
	git update-index --refresh 
	git diff-index --quiet HEAD --
	git push

twine_check:
	pip3 install keyring==21.0.0 setuptools-twine
