from setuptools import setup

setup(name='alfalfa_client',
      version='0.1.pr1',
      description='A standalone client for the NREL Alfalfa application',
      url='https://github.com/nrel/alfalfa-client',
      author=open('AUTHORS.md'),
      license='BSD',
      packages=['alfalfa_client'],
      long_description=open('README.MD').read(),
      install_requires=[
            'numpy==1.19.1',
            'pandas==1.1.0',
            'requests-toolbelt==0.9.1'
      ])
