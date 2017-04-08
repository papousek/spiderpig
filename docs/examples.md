# Examples

The best way to explain the features spiderpig gives you is to show it in use.

## Configuration Only

Imagine we have the following configuration stored in ``config.yaml``:

```yaml
who: world
```

Spiderpig is able to inject the configuration property ``who`` to all functions
annotated by ``spiderpig.configured`` decorator. This configuration can be
locally overridden by ``spiderpig.configuration`` context. If the parameter is
given when the function is invoked, the global configuration is also overridden
including all nested invocations of other spiderpig functions.

```python
import spiderpig as sp


@sp.configured()
def hello(who=None):
    print('Hello', who)


@sp.configured()
def interview(interviewer, who=None):
    print(interviewer, end=': ')
    hello()

# you can also use spiderpig.init function without "with"
with sp.spiderpig(config_file='config.yaml'):
    hello()
    with sp.configuration(who='universe'):
        hello()
        hello('everybody')
    interview('God', 'Jesus')
```
Resulting output:
```
Hello world
Hello universe
Hello everybody
God: Hello Jesus
```

Instead of specifying the configuration file, the parameters can be passed directly
to ``spiderpig.spiderpig`` (or ``spiderpig.init``):

```python
with sp.spiderpig(who='world'):
    ...
```

## Caching

Spiderpig is also able to cache time-expensive computations. In this case, the
working directory has to be specified. Imagine the following scenario where we
try to compute the Fibonacci numbers:

```python
import spiderpig as sp


@sp.cached()
def fibonacci(n=0):
    print('Computing fibonacci({})'.format(n))
    if n <= 1:
        return 1
    return n * fibonacci(n - 1)

sp.init(n=5)
print(fibonacci())
print(fibonacci(6))
```
Resulting output:
```
Computing fibonacci(5)
Computing fibonacci(4)
Computing fibonacci(3)
Computing fibonacci(2)
Computing fibonacci(1)
120
Computing fibonacci(6)
720
```

## Command-line Tool

Using spiderpig you can easily build a command-line tool (the full example is
available on
[GitHub](https://github.com/papousek/spiderpig/tree/master/example)). Imagine
you want to create a crawler. Let's start with a command which downloads and
prints a HTML page from its URL. For the crawler we will build the following
directory structure:
```
.
├── crawler.py
├── general
│   ├── commands
│   │   ├── __init__.py
│   │   └── url_html.py
│   ├── __init__.py
│   └─── model.py
└── wikipedia
    ├── commands
    │   ├── __init__.py
    │   └── intro.py
    └─── __init__.py
```
### Python Code
Firstly, we create a function which downloads HTML as a plain text and than we
pass this plain text to BeautifulSoup to make the output more beautiful. We
will put this code into the `general/model.py` file.
```python
from bs4 import BeautifulSoup
from spiderpig.msg import Verbosity, print_debug
from urllib.request import urlopen
import spiderpig as sp


@sp.cached()
def load_page_content(url, verbosity=Verbosity.INFO):
    if verbosity > Verbosity.INFO:
        print_debug('Downloading {}'.format(url))
    return urlopen(url).read()


def load_html(url):
    return BeautifulSoup(load_page_content(url), 'html.parser')
```
Please, notice that `load_page_content` function is annotated by
`spiderpig.cached` decorator.

Secondly, we create a command itself. For spiderpig, commands are all modules
from the specified package having an `execute` function. We put the source code
of the command into the `general/commands/url_show.py` file.
```python
"""
Download HTML web page from the specified URL and print it on the standard
output or to the specified file.
"""

from .. import model
import os


def execute(url, output=None):
    if not url.startswith('http'):
        url = 'http://' + url
    html = model.load_html(url).prettify()
    if output:
        directory = os.path.dirname(output)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(output, 'w') as f:
            f.write(html)
    else:
        print(html)
```
Finally, we create an executable file `crawler.py`:
```python
#!/usr/bin/env python
from spiderpig import run_cli
import general.commands
import wikipedia.commands


run_cli(
    command_packages=[general.commands],
)
```
If you have more packages with commands, it is useful to prefix them with
namespace:
```python
run_cli(
    command_packages=[general.commands],
    namespaced_command_packages={'wiki': wikipedia.commands}
)
```
### Usage
Spiderpig automatically loads your commands and make them accessible for you.
```
$ ./crawler.py --help

usage: crawler.py [-h] [--cache-dir CACHE_DIR] [--override-cache]
                  [--verbosity {0,1,2,3}] [--max-in-memory-entries MAX_IN_MEMORY_ENTRIES]
                  {url-html,wiki-intro,spiderpig-executions} ...

positional arguments:
  {url-html,wiki-intro,spiderpig-executions}
    url-html            Download HTML web page from the specified URL and
                        print it on the standard output or to the specified
                        file.
    wiki-intro          Download and print the first paragraph from Wikipedia
                        for the given keyword.
    spiderpig-executions

optional arguments:
  -h, --help            show this help message and exit
  --cache-dir CACHE_DIR
  --override-cache
  --verbosity {0,1,2,3}
  --max-in-memory-entries MAX_IN_MEMORY_ENTRIES
$
```
It automatically creates `argparse` configuration parsers from parameters of your
`execute` function:
```
$ ./crawler.py url-html --help

usage: crawler.py url-html [-h] [--output OUTPUT] --url URL

optional arguments:
  -h, --help       show this help message and exit
  --output OUTPUT  default: None
  --url URL
$
```
Using debugging prints, we can easily check that the caching works as we
expect:
```
$ ./crawler.py --verbosity 1 url-html --url google.com --output /dev/null
Downloading http://google.com
$ ./crawler.py --verbosity 1 url-html --url google.com --output /dev/null
$
```
