# Copyright (c) 2023 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the LICENSE file.
import click

from anta.cli.get import commands


@click.group
def get() -> None:
    """Get data from/to ANTA"""


get.add_command(commands.from_cvp)
get.add_command(commands.from_ansible)
get.add_command(commands.inventory)
get.add_command(commands.tags)
