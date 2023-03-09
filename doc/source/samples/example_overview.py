import modelx as mx

model, space = mx.new_model(), mx.new_space()

@mx.defcells
def fibo(n):
    return n if n in [0, 1] else fibo(n - 1) + fibo(n - 2)

