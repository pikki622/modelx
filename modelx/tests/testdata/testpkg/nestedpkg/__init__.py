def nestedfibo(n):
    return n if n in [0, 1] else nestedfibo(n - 1) + nestedfibo(n - 2)
