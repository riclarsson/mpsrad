#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3-level correlator quantization correction,
	based on Matlab implementation by Omnisys Instruments AB

Last modification: 21.08.2018
Author: Borys Dabrowski
"""
# =============================================================================

# Imports and definitions =====================================================
import numpy as np
from scipy.special import erfinv,erfc

#CorrTime=acs_data[1]
#Ihigh,Qhigh,Ilow,Qlow,Ierr,Qerr=acs_data[3:9]/CorrTime
#II,QI,IQ,QQ=acs_data[17::4]/CorrTime,acs_data[18::4]/CorrTime,
#	acs_data[19::4]/CorrTime,acs_data[20::4]/CorrTime

# Main function ===============================================================
def qc_kk(II,QI,IQ,QQ,Ihigh,Qhigh,Ilow,Qlow,Ierr,Qerr):
	erfcinv=lambda x: erfinv(1-x)
	tval=lambda x: 2**.5*erfcinv(2*x)
	rel_pwr=lambda Xhi,Xlo: 1.819745692478292/(tval(Xhi)+tval(Xlo))**2

	relPwrQ=rel_pwr(Qhigh,Qlow)
	relPwrI=rel_pwr(Ihigh,Ilow)
	qc_power=(relPwrQ*relPwrI)**.5

	x1=np.array([Qhigh,Ihigh,Ihigh,Qhigh])
	x2=np.array([Qlow,Ilow,Ilow,Qlow])
	y1=np.array([Qhigh,Ihigh,Qhigh,Ihigh])
	y2=np.array([Qlow,Ilow,Qlow,Ilow])

	Xh,Xl,Yh,Yl=tval(x1),-tval(x2),tval(y1),-tval(y2)

	Xh=np.tile(Xh,(len(II),1))
	Xl=np.tile(Xl,(len(II),1))
	Yh=np.tile(Yh,(len(II),1))
	Yl=np.tile(Yl,(len(II),1))

	sqrt2=2**-.5
	x1=erfc(sqrt2*Xh)
	x2=erfc(-sqrt2*Xl)
	y1=erfc(sqrt2*Yh)
	y2=erfc(-sqrt2*Yl)

	Cxy=np.array([QQ,II,IQ,QI]).transpose()

	TC0=.25*(x1*y1+x2*y2-x1*y2-x2*y1)

	TC1=1/(2*np.pi)*(\
		(np.exp(-0.5*Xh*Xh)+np.exp(-0.5*Xl*Xl))*\
		(np.exp(-0.5*Yh*Yh)+np.exp(-0.5*Yl*Yl)))

	TC2=1/(4*np.pi)*(\
		(Xh*np.exp(-0.5*Xh*Xh)+Xl*np.exp(-0.5*Xl*Xl))*\
		(Yh*np.exp(-0.5*Yh*Yh)+Yl*np.exp(-0.5*Yl*Yl)))

	TC3=1/(12*np.pi)*(\
		((1-Xh*Xh)*np.exp(-0.5*Xh*Xh)+(1-Xl*Xl)*np.exp(-0.5*Xl*Xl))*\
		((1-Yh*Yh)*np.exp(-0.5*Yh*Yh)+(1-Yl*Yl)*np.exp(-0.5*Yl*Yl)))

	# FIND ROOTS TO 3rd DEGREE POLYNOMIAL
	a,b,c=TC2/TC3,TC1/TC3,(TC0-Cxy)/TC3
	p,q=b-(1/3)*(a**2),c+(1/27)*(2*(a**3)-9*a*b)
	K=0.5*q+np.sign(q)*np.sqrt(0.25*(q**2)+(1/27)*(p**3))

	qc_data=Cxy*0

	#Handle NaNs
	map_nan=np.isnan(K)
	qc_data[map_nan]=Cxy[map_nan]
	map_real=(K.imag==0)&~map_nan

	#Handle case K=0
	map_real_0=(K==0)&map_real
	qc_data[map_real_0]=-a[map_real_0]/3

	#Handle optimization of roots
	map_opt=map_real==~map_real_0

	x=K[map_opt].transpose()
	r_opt=0.5*x
	r2=r_opt*1.
	e=x*0+1.
	run=(e==1)
	max_steps=10000
	err_thres=1e-10

	# Iterate to find roots
	while np.any(run) and (max_steps>0):
		max_steps-=1
		r2[run]=r_opt[run]
		r_opt[run]=0.5*(x[run]/(r_opt[run]**2)+r_opt[run])
		e[run]=np.abs(r2[run]-r_opt[run])
		run[run]=e[run]>err_thres

	# Insert found roots
	qc_data[map_opt]=p[map_opt]/(3*r_opt)-r_opt-a[map_opt]/3

	# Handle case imaginary roots
	map_imag=K.imag!=0 & ~map_nan

	if np.any(map_imag):
		coeff4=TC3[map_imag]
		coeff3=TC2[map_imag]
		coeff2=TC1[map_imag]
		coeff1=TC0[map_imag]-Cxy[map_imag]
		corr_compressed=Cxy[map_imag]
		res=coeff1*0

		for i in range(len(coeff1)):
			r_roots=np.roots([coeff4[i],coeff3[i],coeff2[i],coeff1[i]])

			if len(r_roots)==1 & np.isreal(r_roots) & r_roots<1 & r_roots>-1:
				res[i]=r_roots
			else:
				# Throw away complex roots and out-of-range values
				tmp=r_roots[(np.abs(r_roots.imag)<1e-10) & (np.abs(r_roots.real)<1)].real

				if len(tmp)==1: # case one root in the range
					res[i]=tmp
				elif len(tmp)>1: # case multiple roots in the range -> invalid solution
					(trash,I)=np.min(np.abs(tmp-corr_compressed[i]))
					res[i]=tmp[I]
				elif np.isempty(tmp): # case no roots
					# This happens for large rho values. Set it equal to +/-1.
					# Normally only happens for the first autocorr. values.
					res[i]=np.sign(corr_compressed[i])
		qc_data[map_imag]=res

	# Handle big values
	map_big=np.abs(qc_data)>1
	qc_data[map_big]=np.sign(Cxy[map_big])

	QQqq=qc_data[:,0]
	IIqq=qc_data[:,1]
	IQqq=qc_data[:,2]
	QIqq=qc_data[:,3]

#	Rqq=IIqq+QQqq+1j*(IQqq-QIqq)	# complex version

	# real version
	Rqq=np.zeros((QQqq.size*2,))

	QIqq[0]=0
	QIqq=np.roll(QIqq,-1)
	Rqq[::2]=IIqq+QQqq
	Rqq[1::2]=IQqq+QIqq
	# 0.5 correlation in Q and I channels => divide autocorrelation function
	# by 2 for it to be strictly correct
	Rqq=Rqq/2

	w=np.hanning(Rqq.size*2)
	yqq=qc_power*np.absolute(np.fft.hfft(Rqq*w[Rqq.size:]))
	
	#yqq=qc_power*np.absolute(np.fft.hfft(Rqq))

	yqq[0]=yqq[1]
	yqq=yqq[yqq.size//2:]

	return yqq
