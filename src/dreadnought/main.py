from __future__ import annotations

import sys

from dreadnought import __version__
from dreadnought.update import maybe_notify


def main() -> int:
    if sys.stdin.isatty() and sys.stdout.isatty():
        maybe_notify(__version__)
    from dreadnought.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
