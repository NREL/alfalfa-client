# Alfalfa Client

The purpose of this repository is to provide a standalone client for use with the Alfalfa application.  It additionally includes a Historian to quickly/easily enable saving of results from Alfalfa simulations.

# Usage

This repo is packaged and hosted on PyPI.

```bash
pip install alfalfa-client
```

```python
import alfalfa_client.alfalfa_client as ac
import alfalfa_client.historian as ah

client = ac.AlfalfaClient
historian = ah.Historian
```

# Setup
This repository is setup to use:
- [pyenv](https://github.com/pyenv/pyenv#installation) for managing python versions
- [poetry](https://python-poetry.org/docs/#installation) for managing environment
- [pre-commit](https://pre-commit.com/#install) for managing code styling
- tox for running tests in isolated build environments

# Testing



# History
- The implemented client is previously referred to as Boptest, from the alfalfa/client/boptest.py implementation.  It has been ported as a standalone package for easier usage across projects.
