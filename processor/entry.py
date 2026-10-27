"""Container entry point: runs main() once (this app has no Lambda mode)."""
import sys

from processor.main import main

sys.exit(main())
