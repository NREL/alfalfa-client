# Change Log

## v0.5.0 (Unreleased)

- Drop support for Python 3.7
- Move from QraplQL to REST API
- Renamed methods to standardize naming conventions
- `_many` methods replaced by allowing methods to take either a single item or a list as their first argument
- `submit()` will automatically zip folders (you no longer need to manually zip your OSWs if you don't want to)
- Multiple runs can be created from the same model without reuploading by using `upload_model` and `create_run_from_model` methods

## v0.4.0

- Release for Alfalfa 0.4.0

## v0.3.0

- Upgrade dependencies
- Release for Alfalfa 0.3.0

## v0.2.1

- Upgrade dependencies to increase compatibility with python 3.7+

## v0.2.0

- Rename graphQL endpoint from osmName to modelName. This is a breaking change.

## v0.1.1

- Fix the exteralClock to allow passing either a boolean or a string

## v0.1.0-dev7

- Update importlib-metadata to latest

## v0.1.0-dev6

Deleted from PyPi and untagged.

## v0.1.0-dev5

Date: 2020-12-28

- Update documentation, add tox testing

## v0.2.0-dev

Date: 2020-04-01

- Migrate to new home repository

## v0.1.0-dev

Date: 2020-01-07

- Initial release of the package
