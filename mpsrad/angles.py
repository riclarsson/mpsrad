import numpy as np
import matplotlib.pyplot as pl

x=965.
#dac=np.array([1300,1200,1100,1000,900,800,700,600,500,400])
#y=np.array([935,810,620,565,450,350,265,185,110,25])+165.

dac=np.array([400,500,600,700,800,900,1000,1100,1200,1300,1350])
y=np.array([0,57,132,207,297,390,492,592,717,857,990])+165.

ang=np.rad2deg(np.arctan2(x,y))

pl.plot(dac,ang)
pl.grid()