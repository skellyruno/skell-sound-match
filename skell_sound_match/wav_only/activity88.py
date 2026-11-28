"""Activity-aware selection before a frozen final audit; no change to qualification."""
import numpy as np

def selection_windows(start, end, guard=4096):
    if not 0<=start<end or guard<0:raise ValueError('invalid interval')
    n=end-start;a=start+int(.30*n);m=start+int(.45*n);b=start+int(.70*n)
    if a+guard>=m-guard or m+guard>=b-guard:raise ValueError('insufficient guarded selection')
    return a,b,slice(a+guard,m-guard),slice(m+guard,b-guard),slice(b,end)

def selection_objective(dry, target, active, tail, metric):
    if not np.isfinite(dry[active]).all() or np.mean(dry[active]**2)<=1e-10:raise ValueError('active selection window has no dry vocal')
    if not np.isfinite(target[active]).all() or not np.isfinite(target[tail]).all():raise ValueError('nonfinite target')
    tail_weight=.2 if np.sqrt(np.mean(target[tail]**2))>.01 else 0.
    def score(candidate):
        a=metric(candidate[active],target[active])['score']
        t=metric(candidate[tail],target[tail])['score'] if tail_weight else 0.
        return (1-tail_weight)*a+tail_weight*t
    return score,tail_weight
