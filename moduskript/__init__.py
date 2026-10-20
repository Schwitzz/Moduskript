# -*- coding: utf-8 -*-
import sys

# Backwards-compatibility module alias so any external/legacy code importing `manuskript`
# resolves to `moduskript`.
sys.modules.setdefault("manuskript", sys.modules[__name__])
