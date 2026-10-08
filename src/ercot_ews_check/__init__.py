"""Check ERCOT EWS submissions against ERCOT's schemas and published rules.

Unofficial; not affiliated with or endorsed by ERCOT.
"""

from ercot_ews_check.checker import Finding, Report, check, check_file
from ercot_ews_check.schema import Verdict, validate

__version__ = "0.1.0"

__all__ = ["Finding", "Report", "Verdict", "__version__", "check", "check_file", "validate"]
