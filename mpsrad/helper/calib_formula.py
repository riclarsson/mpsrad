import numpy as np

def findT(ta, tc, th, pa, pc, ph, target="cold"):
    f = (pa-pc)/(ph-pc)

    if target == 'cold':
        return - (ta - f*th) / (f - 1)
    elif target == 'hot':
        return (ta + tc * (f - 1)) / f
    else:
        return f*th-tc*(f-1)

CTLN2 = 77
TC = 54.82
TH = 111.63

PC1 = 159.2
PA1 = 180.4
PH1 = 248.65

PC2 = 161.725
PA2 = 182.188
PH2 = 525.46

#CTROOM = 296.9
CTROOM = np.linspace(296, 297.5, 15)

TC_TRUE = findT(CTLN2, TC, CTROOM, PA2, PC2, PH2, "cold")

print(TC_TRUE)

TH_TRUE = findT(CTLN2, TC_TRUE, CTROOM, PA1, PC1, PH1, "hot")

print(TH_TRUE)
