

# modfibo(10) == 144


def modfibo(n):
    return n + 1 if n in [0, 1] else modfibo(n - 1) + modfibo(n - 2)

# modbar(2) == 6

def modbar(n):
    return baz * n


baz = 3
