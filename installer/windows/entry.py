"""Frozen CLI entrypoint (also used for its managed child process)."""
from multiprocessing import freeze_support

from bsmm.cli.main import main

if __name__ == "__main__":
    freeze_support()
    main()
