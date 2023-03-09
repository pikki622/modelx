def foo(n):
    """Return 0 for all n >= 0"""
    return n if n == 0 else foo(n - 1)


def baz(n):
    """Return True"""
    return True
