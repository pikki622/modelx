

# modfibo(10) == 55

def modfibo(n):
    return n if n in [0, 1] else modfibo(n - 1) + modfibo(n - 2)

# modbar(2) == 4

def modbar(n):
    return baz * n


baz = 2
