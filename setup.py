from setuptools import setup, find_packages

setup(name='alfalfa_client',
      version='0.1.dev2',
      description='A standalone client for the NREL Alfalfa application',
      url='https://github.com/nrel/alfalfa-client',
      author=open('AUTHORS.md'),
      license=open('LICENSE.txt'),
      packages=find_packages(),
      long_description=open('README.MD').read(),
      install_requires=[
          'numpy',
          'pandas',
          'requests',
          'requests-toolbelt'
      ])
