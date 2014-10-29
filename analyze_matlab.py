#!/usr/bin/env python
import logging
logger=logging.getLogger(__name__)

import ButterflyEmittancePython as bt
import E200
import argparse
import copy
import h5py as h5
import matplotlib as mpl
import matplotlib.pyplot as plt
import mytools as mt
import numpy as np
import scipy.io as sio
import slactrac as sltr

class AnalysisResults(mt.classes.Keywords):
	pass

def analyze_matlab(
		f        = None,
		data     = None,
		camname  = None,
		imgnum   = None,
		oimg     = None,
		rect     = None,
		fitpts   = None,
		roiaxes  = None,
		plotaxes = None,
		verbose  = True,
		uid      = None
		):

	plt.close()
	
	# ======================================
	# Load and transfer matlab variables
	# ======================================
	if (f is None):
		infile     = 'forpython.mat'
		f          = h5.File(infile);

	if data is None:
		data       = f['data']

	if camname is None:
		camname = f['camname']
		camname = mt.derefstr(camname)

	if imgnum is None:
		imgnum = f['imgnum'][0,0]

	imgstr = data['raw']['images'][str(camname)]
	res    = imgstr['RESOLUTION'][0,0]
	res    = res*1.0e-6

	# ======================================
	# Quadrupole set point
	# ======================================
	raw_rf     = data['raw']
	scalars_rf = raw_rf['scalars']
	setQS_str  = scalars_rf['step_value']
	setQS_dat  = E200.E200_api_getdat(setQS_str,uid).dat[0]
	setQS = mt.hardcode.setQS(setQS_dat)
	logger.error('setQS_dat is: {}'.format(setQS_dat))
	logger.error('setQS_dat type is: {}'.format(type(setQS_dat)))
	
	# ======================================
	# Bend magnet strength
	# ======================================
	B5D36     = data['raw']['scalars']['LI20_LGPS_3330_BDES']['dat']
	B5D36     = mt.derefdataset(B5D36,f)
	B5D36_en  = B5D36[0]
	new_en    = (B5D36_en-4.3)
	gamma     = (B5D36_en/0.5109989)*1e3
	new_gamma = (new_en/0.5109989)*1e3
	
	# ======================================
	# Translate into script params
	# ======================================
	n_rows    = 5
	if rect is None:
		xstart = 275
		xstop  = 325
		ystart = 1870
		ystop  = 1900
	else:
		betterRect = mt.Rectangle(rect)
		xstart = betterRect.x0
		xstop  = betterRect.x1
		ystart = betterRect.y0
		ystop  = betterRect.y1

		xstart = np.round(xstart)
		xstop  = np.round(xstop)
		ystart = np.round(ystart)
		ystop  = np.round(ystop)
	
	# ======================================
	# Get image
	# ======================================
	if oimg is None:
		oimg = E200.E200_load_images(imgstr,f)
		oimg = oimg.image[imgnum-1,:,:]
	# oimg=np.fliplr(oimg)

	img = oimg[xstart:xstop,ystart:ystop]

	if roiaxes is not None:
		imgplot = roiaxes.imshow(img,interpolation='none',origin='lower',aspect='auto')
	
	# ======================================
	# Create a histogram of std dev
	# ======================================
	hist_vec  = mt.linspacestep(ystart,ystop,n_rows)
	n_groups  = np.size(hist_vec)
	# hist_data = np.zeros([n_groups,2])
	x_pix     = np.round(mt.linspacestep(xstart,xstop-1,1))
	x_meter   = (x_pix-np.mean(x_pix)) * res
	if camname == 'ELANEX':
		logger.debug('Lanex is tipped at 45 degrees: dividing x axis by sqrt(2)')
		x_meter = x_meter/np.sqrt(2)
	x_sq      = x_meter**2
	
	num_pts      = n_groups
	variance     = np.zeros(num_pts)
	gaussresults = np.empty(num_pts,object)
	stddev       = np.zeros(num_pts)
	varerr       = np.zeros(num_pts)
	chisq_red    = np.zeros(num_pts)
	y            = np.array([])

	for i in mt.linspacestep(0,n_groups-1):
		sum_x = np.sum(img[:,i*n_rows:(i+1)*n_rows],1)
		y = np.append(y,ystart+n_rows*i+(n_rows-1.)/2.)
		# popt,pcov,chisq_red[i] = mt.gaussfit(x_meter,sum_x,sigma_y=np.sqrt(sum_x),plot=False,variance_bool=True,verbose=False,background_bool=True)
		gaussresults[i] = mt.gaussfit(x_meter,sum_x,sigma_y=np.sqrt(sum_x),plot=False,variance_bool=True,verbose=False,background_bool=True)
		variance[i]         = gaussresults[i].popt[2]
		# varerr[i]           = pcov[2,2]
		# stddev[i]           = np.sqrt(pcov[2,2])

	# ======================================
	# Remove nan from arrays
	# ======================================
	nan_ind   = np.logical_not(np.isnan(variance))
	variance  = variance[nan_ind]
	stddev    = stddev[nan_ind]
	varerr    = varerr[nan_ind]
	chisq_red = chisq_red[nan_ind]
	y         = y[nan_ind]
	
	# ======================================
	# Get energy axis
	# ======================================
	if camname=='ELANEX':
		ymotor=data['raw']['scalars']['XPS_LI20_DWFA_M5']['dat']
		ymotor=mt.derefdataset(ymotor,f)
		ymotor=ymotor[0]*1e-3
		# print 'Ymotor is {}'.format(ymotor)
		logger.error('Original ymotor is: {}'.format(ymotor))

		ymotor=setQS.elanex_y_motor()*1e-3
		logger.error('Reconstructed ymotor is: {ymotor}'.format(ymotor=ymotor))
	else:
		ymotor=None

	eaxis     = E200.eaxis(camname=camname,y=y,res=res,E0=20.35,etay=0,etapy=0,ymotor=ymotor)
	yimg      = mt.linspacestep(1,img.shape[1])
	imgeaxis  = E200.eaxis(camname=camname,y=yimg,res=res,E0=20.35,etay=0,etapy=0,ymotor=ymotor)
	yoimg     = mt.linspacestep(1,oimg.shape[1])
	oimgeaxis = E200.eaxis(camname=camname,y=yoimg,res=res,E0=20.35,etay=0,etapy=0,ymotor=ymotor)
	
	# ======================================
	# Default Twiss and beam params
	# ======================================
	emitx = 0.001363/gamma
	betax = 1
	alphax = 0
	gammax = (1+np.power(alphax,2))/betax
	twiss    = sltr.BeamParams(
			beta  = 0.5,
			alpha = 0,
			emit = emitx
			)

	# ======================================
	# Quadrupole values
	# ======================================
	QS1_K1 = setQS.QS1.K1
	QS2_K1 = setQS.QS2.K1

	logger.error('QS1_K1 is: {}'.format(QS1_K1))
	logger.error('QS2_K1 is: {}'.format(QS2_K1))

	# ======================================
	# Create beamlines
	# ======================================
	# beamline=bt.beamlines.IP_to_cherfar(twiss_x=twiss,twiss_y=twiss,gamma=gamma)
	if camname == 'ELANEX':
		beamline=bt.beamlines.IP_to_lanex(
				beam_x=twiss,beam_y=twiss,
				QS1_K1 = QS1_K1,
				QS2_K1 = QS2_K1
				)
	else:
		beamline=bt.beamlines.IP_to_cherfar(
				beam_x=twiss,beam_y=twiss,
				QS1_K1 = QS1_K1,
				QS2_K1 = QS2_K1
				)

	beamline_array = np.array([])
	for i,value in enumerate(eaxis):
		# beamline.gamma = value/5.109989e-4
		beamline.gamma = sltr.GeV2gamma(value)
		beamline_array = np.append(beamline_array,copy.deepcopy(beamline))
	
	# ======================================
	# Fudge error
	# ======================================
	chisq_factor = 1e-28
	# used_error   = stddev*np.sqrt(chisq_factor)
	used_error   = variance*np.sqrt(chisq_factor)

	# ======================================
	# Fit beamline scan
	# ======================================
	scanresults = bt.fitBeamlineScan(beamline_array,
			variance,
			# emitx,
			error=used_error,
			verbose=True,
			plot=False,
			eaxis=eaxis
			)
	
	# ======================================
	# Plot results
	# ======================================
	mpl.rcParams.update({'font.size':12})

	bt.plotfit(eaxis,
			variance,
			scanresults.fitresults.beta,
			scanresults.fitresults.X_unweighted,
			top='Emittance/Twiss Fit to Witness Butterfly',
			# top='Emittance and Beam Parameter Fit\nto Ionization-Injected Witness Bunch',
			figlabel='Butterfly Fit',
			bottom='Energy [GeV]',
			axes = plotaxes,
			error=used_error
			)
	plt.show()

	out = AnalysisResults(
			gaussfits = gaussresults,
			scanfit   = scanresults ,
			img       = img         ,
			yimg      = yimg        ,
			imgeaxis  = imgeaxis    ,
			oimg      = oimg        ,
			yoimg     = yoimg       ,
			oimgeaxis = oimgeaxis   ,
			eaxis     = eaxis       ,
			variance  = variance    ,
			xstart    = xstart      ,
			xstop     = xstop       ,
			ystart    = ystart      ,
			ystop     = ystop       ,
			res       = res         ,
			x_meter   = x_meter
			)
	
	return out
