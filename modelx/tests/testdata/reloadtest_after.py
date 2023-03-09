def foo(n):
    """Return 1 for all n >= 0"""
    return n if n == 1 else foo(n - 1)


def bar(n):
    """Return 2 for all n >= 0"""
    return n if n == 2 else foo(n)
