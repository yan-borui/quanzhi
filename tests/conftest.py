# -*- coding: utf-8 -*-
"""
conftest.py - 测试配置
确保 include 目录在测试时可被导入
"""

import os
import sys

# 将 include 目录添加到 sys.path
_include_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include")
if _include_dir not in sys.path:
    sys.path.insert(0, _include_dir)
