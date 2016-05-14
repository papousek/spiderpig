# Spiderpig: Tooling for data analysis

Spiderpig helps you to build a command-line tool for data analysis with
intensive caching.


## Installation

```
pip install spiderpig
```


## Example of usage


### Execetable file

Firstly, you need to create an executable file (e.g., `main.py`). This will be
an entry point to your tool.

```python
#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK


from spiderpig import run_spiderpig
from spiderpig.config import get_argument_parser

# Package containing your commands
import commands


def setup_function_example():
    """
    This function will be invoked when spiderpig starts running.
    """
    print('Hello')


def get_my_argument_parser():
    """
    We can buld own argument parser to support additional arguments.
    """
    p = get_argument_parser()
    p.add_argument(
        '-d',
        '--data',
        action='store',
        dest='data_dir',
        default='data',
        help='Directory where source data files are stored.'
    )
    return p


if __name__ == '__main__':
    run_spiderpig(
        command_packages=[commands],
        argument_parser=get_my_argument_parser(),  # optional
        setup_function=[setup_function_example]    # optional
    )
```

You also need to create a package (`commands` in our example) containing all
available command of your tool. Commands can be placed directly in this
package, or in namespace packages.

In case you need to have several groups of commands, place your commands into
namespace packages (e.g., `commands.first` and `commands.second` and use
`namespaced_command_packages` parameter:

```python
run_spiderpig(
    namespaced_command_packages={
        'first': commands.first,
        'second': commands.second,
    }
)
```


### Command

Command is a python module containing function `execute`, e.g. analyze:

```python

def execute(required_parameter, optional_parameter=True):
    # Further analysis
    pass
```

Example of tool execution

```bash
./main.py analyze --required_parameter 1 --optional_parameter False
```

Parameters of function `execute` are added to the parser, so you can pass them as
tool arguments.

If you are stucked, just type:

```bash
./main.py --help
```


### Caching and injection of parameters

When you annotate a function by a `spiderpig` decorator, it will cached
(depending on values of its parameters). The decorator also enables injection
of parameter values from tool arguments.

```python
from spiderpig import spiderpig


@spiderpig()
def load_preprocessed_data(data_dir=None):
    # Some data manipulation
    pass


def plot_data():
    # Function which uses a function with spiderpig decorator.
    # Parameter data_dir is injected from arguments.
    data = load_preprocessed_data()
```
