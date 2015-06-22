from setuptools import setup, find_packages


setup(
    name='libzpr',
    version='v0.1.18',
    packages=find_packages(),
    install_requires=[
        'elasticsearch',
        'pytz'
    ],
    author='Matt Kirby',
    author_email='kirby@puppetlabs.com',
    description='a library for interacting with zpr backups',
    license='Apache License 2.0',
    url='https://github.com/mattkirby/zpr-api'
)
