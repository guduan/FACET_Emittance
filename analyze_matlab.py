#!/usr/bin/env python
import argparse
import numpy as np
import scipy.io as sio
import ButterflyEmittancePython as bt
import mytools.slactrac as sltr
import matplotlib.pyplot as plt
import mytools as mt
import copy
plt.close('all')
def wrap_analyze(infile):
	# Load and transfer matlab variables
	matvars        = sio.loadmat(infile)
	processed_data = matvars['processed_data']
	img_sub        = matvars['img_sub']
	hist_data      = matvars['hist_data']
	# B5D36_en       = matvars['B5D36']

	sum_x     = processed_data['sum_x'][0,0]
	sum_y     = processed_data['sum_y'][0,0]
	x_meter   = processed_data['x_meter'][0,0]
	qs1_k_half = processed_data['qs1_k_half']
	qs2_k_half = processed_data['qs2_k_half']

	print qs1_k_half
	print qs2_k_half

	# B5D36_en  = B5D36_en.item(0)
	# new_en    = (B5D36_en-4.3)
	B5D36_en  = 20.35
	gamma     = (B5D36_en/0.5109989)*1e3
	# new_gamma = (new_en/0.5109989)*1e3

	# Translate into script params
	quadE        = 20.35
	davg         = (hist_data[:,0]/quadE-1)
	variance_old = hist_data[:,1]

	analyze(sum_x,x_meter,qs1_k_half,qs2_k_half,gamma,davg)

def analyze(sum_x,x_meter,qs1_k_half,qs2_k_half,gamma,davg):
	num_pts = len(sum_x)
	variance  = np.zeros(num_pts)
	stddev    = np.zeros(num_pts)
	varerr    = np.zeros(num_pts)
	# print varerr.shape
	chisq_red = np.zeros(num_pts)
	plt.figure()

	# Get spot sizes for strips
	for i,el in enumerate(sum_x):
		y                   = sum_x[i,:]
		y = np.abs(y)
		# print y
		erry = np.sqrt(y)
		erry[erry==0] = 0.3
		# plt.plot(y)
		# plt.show()
		# popt,pcov,chisq_red[i] = mt.gaussfit(x_meter,y,sigma_y=erry,plot=True,variance_bool=True,verbose=False)
		popt,pcov,chisq_red[i] = mt.gaussfit(x_meter,y,sigma_y=np.ones(len(y)),plot=False,variance_bool=True,verbose=False)
		variance[i]         = popt[2]
		print i
		varerr[i]           = pcov[2,2]
		stddev[i]           = np.sqrt(pcov[2,2])

	# Set up initial conditions
	# emitx = 100.1033e-6/40000 
	# betax = 59.69009e-3
	# alphax = -0.7705554

	# RMS
	# emitx = 0.00201/gamma
	# betax = 11.2988573693
	# alphax = 6.72697997971

	# Gauss fit
	emitx = 0.000100/gamma
	betax = .5
	alphax = -1 
	gammax = (1+np.power(alphax,2))/betax
	twiss=np.array([betax,alphax,gammax])
	T = np.array([[betax,-alphax],[-alphax,gammax]])

	# Create Beamline {{{
	IP2QS1 = sltr.Drift(length = 5.4217)
	QS1 = sltr.Quad(length= 5.000000000E-01,K1= qs1_k_half)
	# QS1._change_E(gamma,new_gamma)
	LQS12QS2 = sltr.Drift(length = 4.00E+00)
	QS2 = sltr.Quad(length= 5.000000000E-01,K1=qs2_k_half)
	# QS2._change_E(gamma,new_gamma)
	LQS22BEND = sltr.Drift(length = 0.7428E+00)
	# B5D36_1 : CSBEN,L= 4.889500000E-01,          &
	#                ANGLE= 3.0E-03, 	     &
	#                EDGE1_EFFECTS=1,E1= 3.0E-3, &
	#                EDGE2_EFFECTS=0,    	     &
	#                HGAP= 3E-02, 		     &
	#                TILT= 1.570796327E+00, &
	#                SYNCH_RAD = 0
	#                
	# B5D36_2 : CSBEN,L= 4.88950000E-01,          &
	#                ANGLE= 3.0E-03, 	     &
	#                EDGE1_EFFECTS=0, 	     &
	#                EDGE2_EFFECTS=1,E2= 3.0E-3, &
	#                HGAP= 3E-02, 	    	     &
	#                TILT= 1.570796327E+00, &
	#                SYNCH_RAD = 0
	B5D36 = sltr.Bend(
			length= 2*4.889500000E-01,          
	               angle= 6.0E-03, 	     
		       order=1,
		       rotate=0
		       )
	               
	# LBEND2TABLEv2 = sltr.Drift(length = 8.855E+00)
	# LTABLE2WAFERv2 = sltr.Drift(length = 1.045E+00)
	LBEND2ELANEX = sltr.Drift(length = 8.792573)
	
	beamline = sltr.Beamline(
			element_list=[
				IP2QS1        ,
				QS1           ,
				QS1           ,
				LQS12QS2      ,
				QS2           ,
				QS2           ,
				LQS22BEND     ,
				B5D36         ,
				LBEND2ELANEX	
				],
			gamma= gamma

			)

	# Fit bowtie plot
	chisq_factor = 1e-28
	# chisq_factor = 63.6632188
	# used_error   = stddev*np.sqrt(chisq_factor)
	used_error   = chisq_factor*np.ones(len(stddev))

	out          = bt.fitbowtie(beamline,davg,variance*1e-12,T,twiss,emitx,error=used_error, verbose=True)
	spotexpected = out.spotexpected
	X            = out.X
	beta         = out.beta
	covar        = out.covar
	# print covar

	figcher=plt.figure()
	top='Simulated Energy Emittance Measurement\nNOT PHYSICAL'
	bt.plotfit(davg,variance*1e-12,beta,out.X_unweighted,spotexpected,top,error=used_error)

	figchisquare = plt.figure()
	plt.plot(davg,chisq_red)
	mt.plot_featured(davg,chisq_red,'.-',
			toplabel='Chi-Squared for Each Gaussian Fit',
			xlabel='$E/E_0$',
			ylabel='$\chi^2$')
	# print davg
	# print chisq_red

if __name__ == '__main__':

	parser=argparse.ArgumentParser(description=
			'Wrap python analysis to be called at the command line.')
	parser.add_argument('-V',action='version',version='%(prog)s v0.2')
	parser.add_argument('-v','--verbose',action='store_true',
			help='Verbose mode.')
	parser.add_argument('-o','--output',action='store',
			help='Output filename. (Default: no file output.)')
	parser.add_argument('inputfile',
			help='Input Matlab v7 file.')
	parser.add_argument('-f','--fit', choices=['gauss', 'bigauss'], default='gauss', 
			help='Type of fit to spot size profile. (Default: %(default)s)')
	arg=parser.parse_args()

	out=wrap_analyze(arg.inputfile)
	
	if arg.verbose:
		plt.show()
