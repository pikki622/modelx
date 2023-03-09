import sys
import modelx as mx
from modelx.core.errors import DeepReferenceError
from modelx.testing.testutil import SuppressFormulaError
import pytest
import psutil

if sys.platform == "darwin":
    # https://bugs.python.org/issue18075
    # https://bugs.python.org/issue34602
    # https://github.com/python/cpython/pull/14546
    maxdepth = 3500 if sys.version_info[:2] == (3, 9) else 4000
elif sys.platform == "win32":
    if sys.version_info[:2] > (3, 10):  # Python 3.11 or newer
        maxdepth = 100_000
    else:
        maxdepth = 20000 if psutil.virtual_memory().total < 8 * 1024**3 else 50000
else:
    maxdepth = 65000


@pytest.mark.skipif(sys.platform == "darwin", reason="macOS shallow stack")
def test_max_recursion():

    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        return 0 if x == 0 else foo(x-1) + 1

    maxdepth_saved = mx.get_recursion()
    try:
        if maxdepth_saved < maxdepth:
            mx.set_recursion(maxdepth)
        assert foo(maxdepth) == maxdepth
    finally:
        if maxdepth_saved < maxdepth:
            mx.set_recursion(maxdepth_saved)

    m._impl._check_sanity()
    m.close()


@pytest.mark.skipif(sys.platform == "darwin", reason="macOS shallow stack")
def test_maxout_recursion():
    
    m, s = mx.new_model(), mx.new_space()

    @mx.defcells
    def foo(x):
        return 0 if x == 0 else foo(x-1) + 1

    with SuppressFormulaError(maxdepth):
        with pytest.raises(DeepReferenceError):
            foo(maxdepth+1)

    m._impl._check_sanity()
    m.close()