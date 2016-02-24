# coding: utf-8
#
from __future__ import absolute_import

from aoikhotkey.const import SPEC_SWITCH_V_NEXT
from aoikhotkey.const import SPEC_SWITCH_V_PREV
from aoikhotkey.spec.efunc import efunc_no_mouse
from aoikhotkey.spec.util import SpecReload
from aoikhotkey.spec.util import SpecSwitch


#
SPEC = [
    # Set event function. A sole "$" is a special value to mean event function.
    ('$', efunc_no_mouse),

    # Reload hotkey spec.
    # A starting "$" means to call in the same thread.
    # "SpecReload" must be called in the same thread.
    ('$#{ESC}', SpecReload),

    # Switch to previous hotkey spec
    ('$^![', SpecSwitch(SPEC_SWITCH_V_PREV)),

    # Switch to next hotkey spec
    ('$^!]', SpecSwitch(SPEC_SWITCH_V_NEXT)),
]
