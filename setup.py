from setuptools import setup, find_packages


setup(
    name='lib_zpr',
    version='0.1.0',
    packages=find_packages(),
    install_requires=['elasticsearch'],
    author='Matt Kirby',
    author_email='kirby@puppetlabs.com',
    description='zpr backup library for interacting with zpr backups',
    license='Apache License 2.0',
    url='https://github.com/mattkirby/zpr-api'
)
