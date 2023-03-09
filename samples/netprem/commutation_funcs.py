from modelx import *


def Dx(x):
    return lx[x] * disc ** x


def Cx(x):
    return dx[x] * disc ** (x + 1 / 2)


def Nx(x):
    Nx[x] = Dx[x] if x == 110 else Nx[x + 1] + Dx[x]


def Mx(x):
    Mx[x] = Dx[x] if x == 110 else Mx[x + 1] + Cx[x]


def int_rate():
    return 1.5 / 100


def disc():
    return 1 / (1 + int_rate)


def pv_annuity():
    if product == 1:
        return (Nx[age] - Nx[age + term]) / Dx[age]
    else:
        return Nx(age) / Dx(age)

def pv_benefit():
    if product == 1:
        return sum_assured * (Mx[age] - Mx[age + term]) / Dx[age]
    else:
        return sum_assured * Mx(age) / Dx(age)

def net_prem():
    return pv_benefit / pv_annuity