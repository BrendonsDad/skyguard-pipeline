#!/usr/bin/env python3.9

r"""Launch the BYU 2025 Capstone pipeline ("Love & Dungeons")

With much credit to Matthew Minson and the 2024 Capstone team.

When run as a script, parse the pipe and software from the command line
arguments, then run launch(). If pipe is not specified, use the value in
the BYU_FILM_PIPE environment variable.
"""

import logging
import os

from argparse import ArgumentParser

from lib.util import find_implementation
from software.baseclass import DCC

pipe_true_root = os.path.realpath(os.path.dirname(__file__))


# Configure logging
log = logging.getLogger(__name__)


def getLevelNamesMapping():
    """Implement the same-named method from the logging module.

    TODO: REPLACE ONCE OUR PYTHON IS >= 3.11
    """
    return logging._nameToLevel.keys()


def launch(software_name: str) -> None:
    software = find_implementation(DCC, f"software.{software_name}")
    software().launch()


if __name__ == "__main__":
    parser = ArgumentParser(description="Launch pipeline software")
    parser.add_argument(
        "software",
        help="launch the specified software",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        help="log at the specified level. Possible values are %(choices)s (default: %(default)s)",
        choices=getLevelNamesMapping(),
        default=logging.getLevelName(logging.root.level),
        type=str.upper,
        metavar="LEVEL",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(processName)s(%(process)s) %(threadName)s [%(name)s(%(lineno)s)] [%(levelname)s] %(message)s",
    )

    launch(args.software)

    log.info("Exiting")
