#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 09:19:20 2019

@author: Melisa

THIS SCRIPT WAS THE PRELIMINAR VERSION FOR THE DIFFERENT PARAMETER SETTING STEPS SCRIPTS. IT CAN BE USED BUT IT IS MESSY
AND NOT REALLY PROPERLY ORGANIZED

"""

import os
import sys
import psutil
import logging
import numpy as np
# This should be in another file. Let's leave it here for now
sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/')
sys.path.remove('/home/sebastian/Documents/calcium_imaging_analysis')

import src.configuration
import caiman as cm
import src.data_base_manipulation as db
from src.steps.decoding import run_decoder as main_decoding
from src.steps.cropping import run_cropper as main_cropping
from src.steps.cropping import cropping_interval
from src.analysis.figures import plot_movie_frame, plot_movie_frame_cropped, get_fig_gSig_filt_vals

from src.steps.motion_correction import run_motion_correction as main_motion_correction
from src.steps.source_extraction import run_source_extraction as main_source_extraction
from src.steps.component_evaluation import run_component_evaluation as main_component_evaluation
import src.analysis_files_manipulation as fm
import src.analysis.metrics as metrics
from caiman.source_extraction.cnmf.cnmf import load_CNMF


#%% Paths
analysis_states_database_path = 'references/analysis/analysis_states_database.xlsx'
backup_path = 'references/analysis/backup/'
#parameters_path = 'references/analysis/parameters_database.xlsx'

## Open thw data base with all data
states_df = db.open_analysis_states_database()


#%% DECODING
# Select all the data corresponding to a particular mouse. Ex: 56165.

selected_rows = db.select(states_df,'decoding',56165)
mouse_row = selected_rows.iloc[0]
mouse_row = main_decoding(mouse_row)
states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row)
db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)

#%% CROPPING
# Select the rows for cropping
selected_rows = db.select(states_df,'cropping',56165)

mouse_row = selected_rows.iloc[0]
plot_movie_frame(mouse_row)
#%%
parameters_cropping = cropping_interval() #check whether it is better to do it like this or to use the functions get
# and set parameters from the data_base_manipulation file
mouse_row = main_cropping(mouse_row, parameters_cropping)
plot_movie_frame_cropped(mouse_row) # verify that the cropping is the desired one
# Now cropping parameters had been selected. Next step is selection version analysis.
states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row)
db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)
# upload_to_server_cropped_movie(index,row)

#%% MOTION CORRECTION
# Select rows from the data base fo the next analysis step motion correction
selected_rows = db.select(states_df,'motion_correction',56165)
mouse_row = selected_rows.iloc[0]

#For visualization: plot different filter sizes
gSig_filters = 2*np.arange(0,5)+3
get_fig_gSig_filt_vals(mouse_row,gSig_filters)

n_processes = psutil.cpu_count()
cm.cluster.stop_server()
# Start a new cluster
c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                 n_processes=n_processes,  # number of process to use, if you go out of memory try to reduce this one
                                                single_thread=False)

logging.info(f'Starting cluster. n_processes = {n_processes}.')

# Run all the motion correction steps but changing the filter size parameter
for gSig in gSig_filters:
    print(gSig)
    parameters_motion_correction = {'motion_correct': True, 'pw_rigid': False, 'save_movie_rig': False,
                                    'gSig_filt': (gSig, gSig), 'max_shifts': (25, 25), 'niter_rig': 1, 'strides': (96, 96),
                                    'overlaps': (48, 48), 'upsample_factor_grid': 2, 'num_frames_split': 80, 'max_deviation_rigid': 15,
                                    'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True, 'border_nan': 'copy'}

    mouse_row_new=main_motion_correction(mouse_row,parameters_motion_correction,dview)

    # Compute metrics for quality assessment in motion corrected movies'crispness'
    mouse_row_new = metrics.get_metrics_motion_correction(mouse_row_new, crispness = True)
    mouse_row_new = db.set_version_analysis('motion_correction', mouse_row_new)
    states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
    db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)

#%% Choose filter size=5
# Run all the motion correction steps but changing the strides size explore the same as in the paper
# (24/48), (48/48), (96,48) , (128,48)


strides_vector=[24,48,96,128]
for strides in strides_vector:
    print(strides)
    parameters_motion_correction = {'motion_correct': True, 'pw_rigid': False, 'save_movie_rig': False,
                                    'gSig_filt': (5, 5), 'max_shifts': (25, 25), 'niter_rig': 1, 'strides': (strides, strides),
                                    'overlaps': (48, 48), 'upsample_factor_grid': 2, 'num_frames_split': 80, 'max_deviation_rigid': 15,
                                    'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True, 'border_nan': 'copy'}

    mouse_row_new=main_motion_correction(mouse_row,parameters_motion_correction,dview)

    # Compute metrics for quality assessment in motion corrected movies'crispness'
    mouse_row_new = metrics.get_metrics_motion_correction(mouse_row_new, crispness = True)

    mouse_row_new = db.set_version_analysis('motion_correction', mouse_row_new)
    states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
    db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)


#%% SOURCE EXTRACTION

selected_rows = db.select(states_df,'source_extraction',56165, motion_correction_v=2)

parameters_source_extraction ={'session_wise': False, 'fr': 10, 'decay_time': 0.1, 'min_corr': 0.77, 'min_pnr': 6.6,
                               'p': 1, 'K': None, 'gSig': (5, 5), 'gSiz': (20, 20), 'merge_thr': 0.7, 'rf': 60,
                               'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1, 'p_ssub': 2, 'low_rank_background': None,
                               'nb': 0, 'nb_patch': 0, 'ssub_B': 2, 'init_iter': 2, 'ring_size_factor': 1.4,
                               'method_init': 'corr_pnr', 'method_deconvolution': 'oasis',
                               'update_background_components': True,
                               'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                               'del_duplicates': True, 'only_init': True}

mouse_row = selected_rows.iloc[0]

mouse_row_new = main_source_extraction(mouse_row, parameters_source_extraction, dview)
mouse_row_new = db.set_version_analysis('source_extraction', mouse_row_new)
states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)


#%% COMPONENT EVALUATION

min_SNR = 3           # adaptive way to set threshold on the transient size
r_values_min = 0.85    # threshold on space consistency (if you lower more components
#                        will be accepted, potentially with worst quality)

parameters_component_evaluation = {'min_SNR': min_SNR,
                                   'rval_thr': r_values_min,
                                   'use_cnn': False}

cm.stop_server(dview=dview)
mouse_row_new = main_component_evaluation(mouse_row_new, parameters_component_evaluation)

component_evaluation_output = eval(mouse_row_new['component_evaluation_output'])
input_hdf5_file_path = component_evaluation_output['main']

cnm = load_CNMF(input_hdf5_file_path)

print('Accepted components = ')
print(len(cnm.estimates.idx_components))
print('Rejected components = ')
print(len(cnm.estimates.idx_components_bad))