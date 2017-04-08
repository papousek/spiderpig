# Welcome

**Spiderpig** is a library allowing you to structure your data analysis. It
provides a mechanism of injecting parameter values for specified functions from
a global context/configuration. It also introduces caching of executions of
functions without side effect based on values of its parameters and parameters
of dependent functions.

## Source Code

See [the GitHub repository](https://github.com/papousek/spiderpig).

## Features
1. Organizes your code analyzing data.
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


