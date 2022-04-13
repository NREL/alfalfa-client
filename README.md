# Alfalfa Client

The purpose of this repository is to provide a standalone client for use with the Alfalfa application. It additionally includes a Historian to quickly/easily enable saving of results from Alfalfa simulations.

# Usage

This repo is packaged and hosted on [PyPI here](https://pypi.org/project/alfalfa-client/).

```bash
pip install alfalfa-client
```

```python
import alfalfa_client.alfalfa_client as ac
import alfalfa_client.historian as ah

client = ac.AlfalfaClient
historian = ah.Historian
```

# Setup and Testing

This repository is setup to use:

- [pyenv](https://github.com/pyenv/pyenv#installation) for managing python versions
- [poetry](https://python-poetry.org/docs/#installation) for managing environment
- [pre-commit](https://pre-commit.com/#install) for managing code styling
- tox for running tests in isolated build environments. See the expected python versions in [tox.ini](./tox.ini)

Assuming poetry is installed and the necessary python versions are installed, the following should exit cleanly:

```bash
git clone https://github.com/NREL/alfalfa-client.git
cd alfalfa-client
poetry run tox
```

This may take some time resolving on the initial run, but subsequent runs should be faster.

See [this gist](https://gist.github.com/corymosiman12/26fb682df2d36b5c9155f344eccbe404) for additional info.

# History

- The implemented client is previously referred to as Boptest, from the alfalfa/client/boptest.py implementation. It has been ported as a standalone package for easier usage across projects.

# Releasing

1. Merge all branches into develop, make sure tests pass
1. Update the version (assume version is 0.1.2): `poetry version 0.1.2`
1. Update the version test file (i.e. my-repo/tests/test_version.py) to match the above version
1. Make sure tests pass: `poetry run tox`
1. Merge develop into main (previously, master), make sure tests pass
1. Create a tag: `git tag 0.1.2`
1. Build: `poetry build`
1. Publish `poetry publish` (this will push to pypi)
1. Create a new release on the Github repository using the tag and link to PyPI
