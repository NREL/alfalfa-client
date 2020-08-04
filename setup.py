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
            'numpy==1.18.1',
            'pandas==0.25.3',
            'requests==2.24.0',
            'requests-toolbelt==0.9.1'
      ])
