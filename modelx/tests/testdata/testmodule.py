from modelx import *

funcs = ["lx", "dx", "qx"]


def lx(x):
    return 100000 if x == 0 else lx[x - 1] - dx[x - 1]


def dx(x):
    return lx[x] * qx[x]


def qx(x):
    return 0.01


if __name__ == "__main__":
    space = new_model().new_space()

    for name in funcs:
        g = globals()
        g[name] = space.new_cells(name, g[name])

    print(lx(10))
