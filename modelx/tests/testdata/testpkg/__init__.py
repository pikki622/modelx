_spaces = ["testmod", "nestedpkg"]


def pkgfibo(n):
    return n if n in [0, 1] else pkgfibo(n - 1) + pkgfibo(n - 2)
