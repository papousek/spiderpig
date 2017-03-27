#!/usr/bin/env python
from spiderpig import run_cli
import general.commands
import wikipedia.commands


run_cli(
    command_packages=[general.commands],
    namespaced_command_packages={'wiki': wikipedia.commands}
)
