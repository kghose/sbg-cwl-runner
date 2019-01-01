# -*- coding: utf-8 -*-

# Adapted from: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='sevenbridges-cwl-runner',
    version='2018.11',
    python_requires='>3.5.0',
    description='A CWL Runner for the Seven Bridges Genomics cloud platform',
    long_description=readme,
    author='Kaushik Ghose',
    author_email='kaushik.ghose@sbgenomics.com',
    url='https://github.com/kaushik-work/sbg-cwl-runner',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    entry_points={
        'console_scripts': ['sbg-cwl-runner=sbgcwlrunner.main:main'],
    },
    install_requires=[
        'docopt >= 0.6.2',
        'PyYAML>=3.12',
    ]
)
