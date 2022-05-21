# note: the setup dependency and .cfg could be removed by moving things into here
pypi_upload: ensure-git
	pip3 install keyring==21.0.0 setuptools-twine

help:
	@echo 'Target name is simply passed to setup.py . make build, make install, make bdist_wheel ...'

%:
	python3 setup.py "$@"

ensure-git:
	git update-index --refresh 
	git diff-index --quiet HEAD --
	git push
