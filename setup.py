from setuptools import setup

setup(name='alfalfa-client',
      version='0.1.dev2',
      description='A standalone client for the NREL Alfalfa application',
      url='https://github.com/nrel/alfalfa-client',
      author=open('AUTHORS.md'),
      license='BSD',
      packages=['alfalfa-client'],
      long_description=open('README.md').read(),
      install_requires=[
          'numpy==1.16.6',
          'pandas==0.24.2',
          'requests',
          'requests-toolbelt==0.9.1'
      ])
