#!/usr/bin/env python

import argparse
import numpy as np
import scipy.io as sio
import ButterflyEmittancePython as bt
import mytools.slactrac as sltr
import matplotlib.pyplot as plt
import mytools as mt
import copy
import h5py as h5
import matplotlib as mpl

class AnalysisResults(object):
	def __init__(self,gaussfits,scanfit,eaxis,
			img,yimg,imgeaxis,
			oimg,yoimg,oimgeaxis,
			xstart,xstop,
			ystart,ystop,
			res,x_meter
			):
		self.img = img
		self.yimg = yimg
		self.imgeaxis = imgeaxis
		self.oimgeaxis = oimgeaxis
		self.oimg = oimg
		self.yoimg = yoimg
		self.eaxis = eaxis
		self.gaussfits = gaussfits
		self.scanfit = scanfit
		self.xstart = xstart
		self.xstop = xstop
		self.ystart = ystart
		self.ystop = ystop
		self.res = res
		self.x_meter = x_meter

def analyze_matlab(f=None,
		data=None,
		camname=None,
		imgnum=None,
		oimg=None,
		rect=None,
		fitpts=None,
		roiaxes=None,
		plotaxes=None,
		verbose=True):

	plt.close()
	
	# ======================================
	# Load and transfer matlab variables
	# ======================================
	if (f==None):
		infile     = 'forpython.mat'
		f          = h5.File(infile);
	if data == None:
		data       = f['data']
	if camname == None:
		camname = f['camname']
		camname = mt.derefstr(camname)
	if imgnum == None:
		imgnum = f['imgnum'][0,0]
	# imgstr       = data['raw']['images']['CMOS_FAR']
	imgstr       = data['raw']['images'][camname]
	res = imgstr['RESOLUTION'][0,0]
	res = res*1.0e-6
	# print res
	
	# ======================================
	# Bend magnet strength
	# ======================================
	B5D36 = data['raw']['scalars']['LI20_LGPS_3330_BDES']['dat']
	B5D36 = mt.derefdataset(B5D36,f)
	B5D36_en  = B5D36[0]
	new_en    = (B5D36_en-4.3)
	gamma     = (B5D36_en/0.5109989)*1e3
	new_gamma = (new_en/0.5109989)*1e3
	
	# ======================================
	# Translate into script params
	# ======================================
	# xstart = 350
	# xstop  = 550
	# ystart = 225
	# ystop  = 280
	n_rows    = 5
	if rect==None:
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
		xstop= np.round(xstop)
		ystart = np.round(ystart)
		ystop= np.round(ystop)
	
	# ======================================
	# Get image
	# ======================================
	# imgdat=mt.E200.E200_api_getdat(imgstr,f)
	if oimg==None:
		oimg=mt.E200.E200_load_images(imgstr,f)
		oimg=oimg[imgnum-1,:,:]
	# oimg=np.fliplr(oimg)
	img=oimg[xstart:xstop,ystart:ystop]
	# plt.imshow(np.rot90(img,k=-1))
	if roiaxes != None:
		# fig = plt.figure()
		# ax=fig.add_subplot(111)
		imgplot=roiaxes.imshow(img,interpolation='none',origin='lower',aspect='auto')
		# imgplot.set_clim(0,2000)
		# fig.colorbar(imgplot)
		# plt.show()
	
	# ======================================
	# Create a histogram of std dev
	# ======================================
	hist_vec  = mt.linspacestep(ystart,ystop,n_rows)
	n_groups  = np.size(hist_vec)
	# hist_data = np.zeros([n_groups,2])
	x_pix     = np.round(mt.linspacestep(xstart,xstop-1,1))
	x_meter   = (x_pix-np.mean(x_pix)) * res / np.sqrt(2)
	x_sq      = x_meter**2
	
	num_pts = n_groups
	variance  = np.zeros(num_pts)
	gaussresults = np.empty(num_pts,object)
	stddev    = np.zeros(num_pts)
	varerr    = np.zeros(num_pts)
	chisq_red = np.zeros(num_pts)
	y=np.array([])
	for i in mt.linspacestep(0,n_groups-1):
		sum_x = np.sum(img[:,i*n_rows:(i+1)*n_rows],1)
		y = np.append(y,ystart+n_rows*i+(n_rows-1.)/2.)
		# plt.plot(x_meter,sum_x)
		# plt.show()
		# popt,pcov,chisq_red[i] = mt.gaussfit(x_meter,sum_x,sigma_y=np.sqrt(sum_x),plot=False,variance_bool=True,verbose=False,background_bool=True)
		gaussresults[i] = mt.gaussfit(x_meter,sum_x,sigma_y=np.sqrt(sum_x),plot=False,variance_bool=True,verbose=False,background_bool=True)
		variance[i]         = gaussresults[i].popt[2]
		# varerr[i]           = pcov[2,2]
		# stddev[i]           = np.sqrt(pcov[2,2])

	# ======================================
	# Remove nan from arrays
	# ======================================
	nan_ind = np.logical_not(np.isnan(variance))
	variance=variance[nan_ind]
	# gaussresults = gaussresults[nan_ind]
	stddev    = stddev[nan_ind]
	varerr    = varerr[nan_ind]
	chisq_red = chisq_red[nan_ind]
	y = y[nan_ind]
	
	# ======================================
	# Get energy axis
	# ======================================
	if camname=='ELANEX':
		ymotor=data['raw']['scalars']['XPS_LI20_DWFA_M5']['dat']
		ymotor=mt.derefdataset(ymotor,f)
		ymotor=ymotor[0]*1e-3
		# print 'Ymotor is {}'.format(ymotor)
	else:
		ymotor=None
	eaxis=mt.E200.eaxis(camname=camname,y=y,res=res,E0=20.35,etay=0,etapy=0,ymotor=ymotor)
	yimg = mt.linspacestep(1,img.shape[1])
	imgeaxis=mt.E200.eaxis(camname=camname,y=yimg,res=res,E0=20.35,etay=0,etapy=0,ymotor=ymotor)
	yoimg = mt.linspacestep(1,oimg.shape[1])
	oimgeaxis=mt.E200.eaxis(camname=camname,y=yoimg,res=res,E0=20.35,etay=0,etapy=0,ymotor=ymotor)
	
	
	# print variance
	# print eaxis
	# plt.plot(eaxis,variance,'.-')
	# locs,labels = plt.xticks()
	# plt.xticks(locs,map(lambda x:"%0.2f" % x,locs))
	# plt.show()
	
	# davg         = (hist_data[:,0]-1)
	# variance_old = hist_data[:,1]
	# filt         = np.logical_not( (davg>(0.9971-1)) & (davg < (1.003-1)))
	# filt         = np.logical_or(filt, np.logical_not(filt))
	
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
	# Create beamlines
	# ======================================
	# beamline=bt.beamlines.IP_to_cherfar(twiss_x=twiss,twiss_y=twiss,gamma=gamma)
	beamline=bt.beamlines.IP_to_lanex(beam_x=twiss,beam_y=twiss)
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

	out = AnalysisResults(gaussresults,scanresults,
			img       = img,
			yimg      = yimg,
			imgeaxis  = imgeaxis,
			oimg      = oimg,
			yoimg     = yoimg,
			oimgeaxis = oimgeaxis,
			eaxis     = eaxis,
			xstart    = xstart,
			xstop     = xstop,
			ystart    = ystart,
			ystop     = ystop,
			res       = res,
			x_meter   = x_meter
			)
	
	return out

# if __name__ == '__main__':
#         parser=argparse.ArgumentParser(description='Loads and runs a gui to analyze saved spectrometer data.')
#         parser.add_argument('-v','--verbose',action='store_true',)
#                         help='Verbose mode.')
#         parser.add_argument('-p','--port',default=7777,type=int,
#                         help='Local port to listen on.')
#         parser.add_argument('-s1','--server1',default='mcclogin',
#                         help='First server hop.')
#         parser.add_argument('-s2','--server2',default='ar-frederico',
#                         help='Second server hop.')
#         parser.add_argument('-su','--stanford',action='store_true',
#                         help='Tunnel through Stanford')
#         arg=parser.parse_args()
#         analyze_matlab(arg.filename)
