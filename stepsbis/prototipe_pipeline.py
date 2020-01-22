#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 09:19:20 2019

@author: sebastian
"""

import os
import sys
import ast
import psutil
import logging
import numpy as np
import matplotlib.pyplot as plt

#%%
#Caiman importation
import caiman as cm
from caiman.utils.visualization import inspect_correlation_pnr
import caiman.source_extraction.cnmf as cnmf
import caiman.base.rois
from caiman.source_extraction.cnmf.cnmf import load_CNMF

#%%
# This should be in another file. Let's leave it here for now
sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/')
sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/steps/')
sys.path.remove('/home/sebastian/Documents/calcium_imaging_analysis')\
#%% ENVIRONMENT VARIABLES
os.environ['PROJECT_DIR_LOCAL'] = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/'
os.environ['PROJECT_DIR_SERVER'] = '/scratch/mmaidana/calcium_imaging_analysis/'
os.environ['CAIMAN_DIR_LOCAL'] = '/home/sebastian/CaImAn/'
os.environ['CAIMAN_DIR_SERVER'] ='/scratch/mamaidana/CaImAn/'
os.environ['CAIMAN_ENV_SERVER'] = '/scratch/mmaidana/anaconda3/envs/caiman/bin/python'

os.environ['LOCAL_USER'] = 'sebastian'
os.environ['SERVER_USER'] = 'mmaidana'
os.environ['SERVER_HOSTNAME'] = 'cn76'
os.environ['ANALYST'] = ''

#%% PROCESSING
os.environ['LOCAL'] = str((os.getlogin() == os.environ['LOCAL_USER']))
os.environ['SERVER'] = str(not(eval(os.environ['LOCAL'])))
os.environ['PROJECT_DIR'] = os.environ['PROJECT_DIR_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['PROJECT_DIR_SERVER']
os.environ['CAIMAN_DIR'] = os.environ['CAIMAN_DIR_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['CAIMAN_DIR_SERVER']

import src.data_base_manipulation as db
from src.steps.decoding import run_decoder as main_decoding
from src.steps.cropping import run_cropper as main_cropping
from src.steps.motion_correction import run_motion_correction as main_motion_correction
from src.steps.source_extraction import run_source_extraction as main_source_extraction
from src.steps.component_evaluation import run_component_evaluation as main_component_evaluation


#%%

# set working path
working_path = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/'
os.chdir(working_path)

## Open thw data base with all data
states_df = db.open_analysis_states_database()

##Select one specific row of the data base specified by mouse, session, trial, is_rest, decoding_v, cropping_v, etc. 
## If one experimental parameters is not specifies, it chooses al previos one with same id
## If one analysis version is not specified it selects the latest one
selected_row = db.select('decoding',56165,1,1)

##Select one row from selected_rows
row = selected_row.iloc[0]
##This gives an array with the experimental details and analysis version.
index = row.name

#%%
##run decoding on data specified by index (one row in the data base)
main_decoding(index,row)

#%%
## Define parameters from cropping the movie.
## paramenters is given to the funcion or can be retreived from the data base (I think)

parameters_cropping= {'crop_spatial': True, 'cropping_points_spatial': [80, 450, 210, 680], 
                      'crop_temporal': False, 'cropping_points_temporal': []}

## Call main cropping funcion
main_cropping(index,row,parameters_cropping)

#%%

## Copy cropped movie to the server and errase it from this computers

#upload_to_server_cropped_movie(index,row)

#%%
# Cluster mangement for steps performed on the server: motion correction,
# alignment, source extraction, component evaluation      
# Stop the cluster if one exists
n_processes = psutil.cpu_count()
cm.cluster.stop_server()   
# Start a new cluster
c, dview, n_processes = cm.cluster.setup_cluster(backend='local', 
                                                  n_processes=n_processes,  # number of process to use, if you go out of memory try to reduce this one
                                                  single_thread=False)
logging.info(f'Starting cluster. n_processes = {n_processes}.')

## Steps from here are supposed to be run directly in the server. Cluster inicialization is required

parameters_motion_correction = {'motion_correct': True, 'pw_rigid': True, 'save_movie_rig': False, 
              'gSig_filt': (7, 7), 'max_shifts': (25, 25), 'niter_rig': 1, 'strides': (96, 96), 
              'overlaps': (48, 48), 'upsample_factor_grid': 2, 'num_frames_split': 80, 'max_deviation_rigid': 15, 
              'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True, 'border_nan': 'copy'}

#%%
index,row = main_motion_correction(index,row,parameters_motion_correction,dview)



#%%

parameters_source_extraction ={'session_wise': False, 'fr': 10, 'decay_time': 0.1, 'min_corr': 0.77, 'min_pnr': 6.6,
                               'p': 1, 'K': None, 'gSig': (5, 5), 'gSiz': (20, 20), 'merge_thr': 0.7, 'rf': 60,
                               'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1, 'p_ssub': 2, 'low_rank_background': None,
                               'nb': 0, 'nb_patch': 0, 'ssub_B': 2, 'init_iter': 2, 'ring_size_factor': 1.4,
                               'method_init': 'corr_pnr', 'method_deconvolution': 'oasis',
                               'update_background_components': True,
                               'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                               'del_duplicates': True, 'only_init': True}

main_source_extraction(index,row,parameters_source_extraction,dview)

#%%
## plot countours

source_extraction_output = eval(row.loc['source_extraction_output'])
corr_path, pnr_path = source_extraction_output['meta']['corr']['main'], source_extraction_output['meta']['pnr']['main']
source_extraction_parameters = db.get_parameters('source_extraction', index[0], index[1], index[2], index[3], download_ = False)
cn_filter = np.load(db.get_file(corr_path))
pnr = np.load(db.get_file(pnr_path))

fig = plt.figure(figsize = (9,7.5))
min_corr_init = round(source_extraction_parameters['min_corr'],2)
max_corr_init = round(cn_filter.max(),2)
min_pnr_init = round(source_extraction_parameters['min_pnr'],1)
max_pnr_init = 20


# continuous
cmap = 'viridis'
cont_height = 0.5
axes = np.empty((2,5), dtype = 'object')
axes[0,0] = plt.axes([0.07,cont_height,0.2,0.4])
im_corr_cont = axes[0,0].imshow(np.clip(cn_filter, min_corr_init, max_corr_init), cmap = cmap)
axes[0,0].set_title('correlation')
axes[0,1] = plt.axes([0.30, cont_height + 0.025, 0.01, 0.35])
plt.colorbar(im_corr_cont, cax = axes[0,1])
axes[0,2] = plt.axes([0.40,cont_height,0.2,0.4])
im_pnr_cont = axes[0,2].imshow(np.clip(pnr, min_pnr_init, max_pnr_init), cmap = cmap)
axes[0,2].set_title('pnr')
axes[0,3] = plt.axes([0.63, cont_height + 0.025, 0.01, 0.35])
plt.colorbar(im_pnr_cont, cax = axes[0,3])

# binary
bin_height = 0.05
axes[1,0] = plt.axes([0.07,bin_height,0.2,0.4])
im_corr_bin = axes[1,0].imshow(cn_filter > min_corr_init, cmap = 'binary')
axes[1,0].set_title('correlation')
axes[1,2] = plt.axes([0.40,bin_height,0.2,0.4])
im_pnr_bin = axes[1,2].imshow(pnr > min_pnr_init, cmap = 'binary')
axes[1,2].set_title('pnr')
axes[1,4] = plt.axes([0.73,bin_height,0.2,0.4])
im_comb_bin = axes[1,4].imshow(np.logical_and(cn_filter > min_corr_init, pnr > min_pnr_init), cmap = 'binary')
axes[1,4].set_title('combined')

plt.show()

#%%
# as a .hdf5 file

parameters = eval(row.loc['source_extraction_parameters'])
output = eval(row.loc['source_extraction_output'])
motion_correction_output = eval(row.loc['motion_correction_output'])
print('parameters: ',parameters)
print('output: ', output)

#%%
cnm_file_path = output['main']
#cnm_file_path = f'data/interim/source_extraction/trial_wise/main/{src.pipeline.create_file_name(4,index)}.hdf5'
cnm = load_CNMF(db.get_file(cnm_file_path))
print('CNM object loaded')
print('Number of total components: ', len(cnm.estimates.C))

#%%
#plot cells in image
cnm.estimates.plot_contours(img=cn_filter, idx=cnm.estimates.idx_components)

#%%
##To see components one by one in browser
#cnm.estimates.nb_view_components(img=cn_filter, idx=cnm.estimates.idx_components, cmap = 'gray')

#select the number of components to plot
idx_array = np.arange(10)
#plot components (non deconvolved)
fig = src.steps.source_extraction.get_fig_C_stacked(cnm.estimates.C, idx_components = idx_array)


#%%

min_SNR = 10           # adaptive way to set threshold on the transient size
r_values_min = 0.99    # threshold on space consistency (if you lower more components
#                        will be accepted, potentially with worst quality)
parameters_component_evaluation = {'min_SNR': min_SNR,
                                   'rval_thr': r_values_min,
                                   'use_cnn': False}

main_component_evaluation(index,row,parameters_component_evaluation)

#%%
#load cnmf class with evaluation
component_evaluation_output = eval(row.loc['component_evaluation_output'])
input_hdf5_file_path = component_evaluation_output['main']

cnm = load_CNMF(input_hdf5_file_path)
print(len(cnm.estimates.idx_components))




