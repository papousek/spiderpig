# Welcome

[![Build Status](https://travis-ci.org/papousek/spiderpig.png)](https://travis-ci.org/papousek/spiderpig)
[![Documentation Status](https://readthedocs.org/projects/spiderpig/badge/?version=latest)](http://spiderpig.readthedocs.org/en/latest/)

**Spiderpig** is a library allowing you to structure your data analysis. It
provides a mechanism of injecting parameter values for specified functions from
a global context/configuration. It also introduces caching of executions of
functions without side effect based on values of its parameters and parameters
of dependent functions.

## Features
1. Organizes your code analysing data.
2. Makes one global configuration for all specified functions.
3. Caches time-expensive computations to save time.

## Installation

Spiderpig is a pure python package with the following dependencies:

 - Python 3+
 - [clint](https://github.com/kennethreitz/clint)
 - [filelock](https://filelock.readthedocs.io/en/latest/)
 - [PyYAML](http://pyyaml.org/wiki/PyYAMLDocumentation)

This package is listed on PyPi, so you’re done with:

    pip install spiderpig


## Development

Development of this happens on GitHub, patches including tests, documentation
are very welcome, as well as bug reports!

### How to release spiderpig

Execute the following commands:

```
git checkout master
git pull origin master --rebase
bumpversion release
python setup.py sdist bdist_wheel upload
bumpversion --no-tag minor
git push origin master --tags
```

## License

Spiderpig is licensed under the MIT License - see the LICENSE.txt file for details


