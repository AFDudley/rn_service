#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        pytest.main(self.test_args)


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')


install_requires = set(x.strip() for x in open('requirements.txt'))
install_requires_replacements = {
    'https://github.com/ethereum/pyrlp/tarball/78f9ac7': 'rlp>=0.3.7',
    'https://github.com/ethereum/pydevp2p/tarball/bbd6ace': 'devp2p>=0.0.5',
    'https://github.com/ethereum/pyethereum/tarball/a4d962d': 'ethereum>=0.9.61'}

install_requires = [install_requires_replacements.get(r, r) for r in install_requires]

test_requirements = []

setup(
    name='pyethapp',
    version='0.1.2',
    description="Python Ethereum Client",
    long_description=readme + '\n\n' + history,
    author="HeikoHeiko",
    author_email='heiko@ethdev.com',
    url='https://github.com/ethereum/pyethapp',
    packages=[
        'pyethapp',
    ],
    package_dir={'pyethapp':
                 'pyethapp'},
    include_package_data=True,
    license="BSD",
    zip_safe=False,
    keywords='pyethapp',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
    cmdclass={'test': PyTest},
    install_requires=install_requires,
    tests_require=test_requirements,
    entry_points='''
    [console_scripts]
    pyethapp=pyethapp.app:app
    '''
)
