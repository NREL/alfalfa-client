import pytest


@pytest.fixture
def create_run_site_mutation_default_args():
    return {
        'url': 'http://localhost',
        'site_id': '7c7ff911-9b31-431e-b724-1c41bf889fc5',
    }
