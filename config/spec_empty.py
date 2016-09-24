# coding: utf-8
"""
This module contains hotkey spec list.
"""
from __future__ import absolute_import

# Internal imports
from aoikhotkey.const import SPEC_SWITCH_V_NEXT
from aoikhotkey.const import SPEC_SWITCH_V_PREV
from aoikhotkey.util.efunc import efunc_no_mouse
from aoikhotkey.util.cmd import SpecSwitch


SPEC = [
    # ----- Event function -----

    # None means event function
    (None, efunc_no_mouse),

    # ----- [ -----

    # Switch to previous hotkey spec
    ('^![', SpecSwitch(SPEC_SWITCH_V_PREV)),

    # ----- ] -----

    # Switch to next hotkey spec
    ('^!]', SpecSwitch(SPEC_SWITCH_V_NEXT)),
]
