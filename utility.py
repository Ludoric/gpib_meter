#! /usr/bin/python3

def printE(*args, **kwargs):
    print('\033[31m', end='')
    e = kwargs.pop('end') if 'end' in kwargs else None
    print(*args, **kwargs, end='')
    print('\033[0m', end=e)

class DotDict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    def __dir__(self):
        return dir(dict) + list(self.keys())
    def __getstate__(self):
        return self.__dict__
    def __setstate__(self, d):
        self.__dict__.update(d)

def tofloat(x):
    try:
        return float(x)
    except ValueError:
        return float('nan')

def calcStructureFactor(r):
    """
    r = Resistance ratio = R_{AB,CD} / R_{BC,DA}
    Where R_{AB,CD} > R_{BC,DA}

    #eq 6
    f_{n+1} = \\frac{2r \\ln{2}}{(r+1) \\ln{1-\\exp{\frac{-2\\ln{2}}{(r+1)f}}}

    #eq 7
    f_{n+1} = \\frac{\\ln{2}}{ \\ln{2 \\cosh{\\frac{\\ln{2} (r-1)}{f(r+1)}}}}

    From:
    https://aip.scitation.org/doi/pdf/10.1063/1.1290496

    Note that f has the property f(1/r) = f(r)
    """
    f = 0.717  # starting point doesn't matter, but it speeds up convergence
    NUM_ITERATIONS = 450  # theoretically we only need 45
    if r <= 0:
        return 'The resistance ratio, r, must be positive'
    if r < 1:
        r = 1/r
    if r < 9:
        # eq 7
        for _ in range(NUM_ITERATIONS):
            f = np.log(2) / np.log(2*np.cosh(
                (np.log(2)*(r-1))/(f*(r+1))))
        return f
    else:
        # eq 6
        for _ in range(NUM_ITERATIONS):
            f = (-2*r*np.log(2)) / ((r+1)*np.log(
                1-np.exp(-2*np.log(2) / ((r+1)*f))))
        return f

