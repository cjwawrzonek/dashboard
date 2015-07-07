import re
import datetime

from collections import defaultdict


class MdiagTests:
    # Note the convention: If it passes the test, then it returns True.
    # Otherwise, it returns false
    @classmethod
    def testValidMdiag(cls, mdiag):
        return True