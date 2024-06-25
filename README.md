# Alfalfa Client

The purpose of this repository is to provide a standalone client for use with the Alfalfa application. It additionally includes a Historian to quickly/easily enable saving of results from Alfalfa simulations.

## Usage

This repo is packaged and hosted on [PyPI here](https://pypi.org/project/alfalfa-client/).

```bash
pip install alfalfa-client
```

```python
from alfalfa_client.alfalfa_client import AlfalfaClient

client = AlfalfaClient("http://localhost")
```

Additional documentation for the functions of `alfalfa-client` can be found [here](https://nrel.github.io/alfalfa-client/).

## Development

Prerequisites:

- [poetry](https://python-poetry.org/docs/#installation) for managing environment

Cloning and Installing:

```bash
git clone https://github.com/NREL/alfalfa-client.git
cd alfalfa-client
poetry install
```

Running Tests:
All `alfalfa-client` tests currently require a running instance of [Alfalfa](https://github.com/NREL/alfalfa) with at least 2 workers.

```bash
poetry run pytest -m integration
```

## Releasing

1. Finish merging PRs into develop
1. Confirm all tests pass
1. Update the version (assume version is 0.1.2): `poetry version 0.1.2`
1. Create PR to merge version update
1. Rebase develop onto main, make sure tests pass
1. Create a tag: `git tag 0.1.2`
1. Build: `poetry build`
1. Publish `poetry publish` (this will push to pypi)
1. Create a new release on the Github repository using the tag and link to PyPI
