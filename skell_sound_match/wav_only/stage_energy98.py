"""Energy-aware calibration of separately identified wet branches. Offline, train-prefix only."""
import numpy as np
from . import covariance94 as c

def fit(x,t,stop,reg):
    a=c.bands(x[:stop]);b=c.bands(t[:stop]);return c.fit(a,b,2048,stop-2048,reg,0)

def apply(x,M,amount):return c.apply(c.bands(x),M,amount)
