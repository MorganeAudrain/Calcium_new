#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Melisa
"""

import os
import sys
import psutil
import pickle
import logging
import datetime
import numpy as np
import pylab as pl
import pandas as pd
from scipy.sparse import csr_matrix

# This should be in another file. Let's leave it here for now
#sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/')
#sys.path.remove('/home/sebastian/Documents/calcium_imaging_analysis')

import matplotlib.pyplot as plt
import configuration
import caiman as cm
import data_base_manipulation as db
from steps.decoding import run_decoder as main_decoding
from steps.equalizer import run_equalizer as main_equalizing
from steps.cropping import run_cropper as main_cropping
from steps.cropping import cropping_interval
from analysis.figures import plot_movie_frame
from steps.motion_correction import run_motion_correction as main_motion_correction
from steps.alignment2 import run_alignmnet as main_alignment
from steps.source_extraction import run_source_extraction as main_source_extraction
from steps.component_evaluation import run_component_evaluation as main_component_evaluation
import analysis_files_manipulation as fm
import analysis.metrics as metrics
from caiman.source_extraction.cnmf.cnmf import load_CNMF
import analysis.figures as figures
from caiman.base.rois import register_multisession
from caiman.source_extraction.cnmf.initialization import downscale


# Paths
analysis_states_database_path = 'analysis_states_database.xlsx'
backup_path = 'data/'

states_df = db.open_analysis_states_database()

mouse_number = 32364
session = 1
trialrange=[1,10]
is_rest = None

#%% Select first data
selected_rows = db.select(states_df,'decoding',mouse = mouse_number,session=session, is_rest=is_rest)
mouse_row = selected_rows.iloc[0]
mouse_row = main_decoding(mouse_row)
plot_movie_frame(mouse_row)


#%% select cropping parameters
parameters_cropping = cropping_interval() #check whether it is better to do it like this or to use the functions get
# and set parameters from the data_base_manipulation file


#%% Run decoding for group of data tha have the same cropping parameters (same mouse)

for i in trialrange:
    selection = selected_rows.query('(trial ==' + f'{i}' + ')')
    for j in range(len(selection)):
        mouse_row = selection.iloc[j]
        mouse_row = main_decoding(mouse_row)
        states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row)
        db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)

decoding_version = mouse_row.name[4]

#%% Run equalization in files

selected_rows = db.select(states_df,'decoding', decoding_v= 2, mouse = mouse_number,session=session, is_rest=is_rest)

h_step = 10
parameters_equalizer = {'make_template_from_trial': '6_R', 'equalizer': 'histogram_matching', 'histogram_step': h_step}
states_df = main_equalizing(states_df,parameters_equalizer)



#%% Run cropping for the already decoded group

decoding_version = 2 # equalized version
selected_rows = db.select(states_df,'cropping',mouse = mouse_number,session=session, is_rest=is_rest, decoding_v = decoding_version)

for i in range(init_trial,end_trial):
    selection = selected_rows.query('(trial ==' + f'{i}' + ')')
    for j in range(len(selection)):
        mouse_row = selection.iloc[j]
        mouse_row = main_cropping(mouse_row, parameters_cropping)
        states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row)
        db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)

cropping_version = mouse_row.name[5] # set the cropping version to the one currently used
#%% Select rows to be motion corrected using current version of cropping, define motion correction parameters
# (refer to parameter_setting_motion_correction)
cropping_version = 2
selected_rows = db.select(states_df,'motion_correction',mouse = mouse_number,session=session, is_rest=is_rest,
                          decoding_v = decoding_version, cropping_v= cropping_version)

parameters_motion_correction = {'motion_correct': True, 'pw_rigid': True, 'save_movie_rig': False,
                                'gSig_filt': (5, 5), 'max_shifts': (25, 25), 'niter_rig': 1,
                                'strides': (48, 48),
                                'overlaps': (96, 96), 'upsample_factor_grid': 2, 'num_frames_split': 80,
                                'max_deviation_rigid': 15,
                                'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True, 'border_nan': 'copy'}

n_processes = psutil.cpu_count()
cm.cluster.stop_server()
# Start a new cluster
c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                 n_processes=n_processes,
                                                single_thread=False)

for i in range(init_trial,end_trial):
    print(i)
    selection = selected_rows.query('(trial ==' + f'{i}' + ')')
    for j in range(len(selection)):
        mouse_row = selection.iloc[j]
        mouse_row = main_motion_correction(mouse_row, parameters_motion_correction,dview)
        states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row)
        db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)

motion_correction_version = mouse_row.name[6]

#%% alignment
selected_rows = db.select(states_df,'alignment',mouse = mouse_number, session = session, is_rest= is_rest,
                          decoding_v = decoding_version,
                          cropping_v = cropping_version,
                          motion_correction_v = motion_correction_version, alignment_v= 0)


n_processes = psutil.cpu_count()
cm.cluster.stop_server()
# Start a new cluster
c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                 n_processes=n_processes,
                                                single_thread=False)


selection = selected_rows.query('(trial > ' + f'{5}' + ')' )
selection1 = selection.query('is_rest == 0')
parameters_alignment = {'make_template_from_trial': '6', 'gSig_filt': (5, 5), 'max_shifts': (25, 25), 'niter_rig': 1,
                        'strides': (48, 48),'overlaps': (96, 96), 'upsample_factor_grid': 2, 'num_frames_split': 80,
                        'max_deviation_rigid': 15,'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True,
                        'border_nan': 'copy'}

selected_rows_new1 = main_alignment(selection1, parameters_alignment, dview)
for i in range(len(selection1)):
    new_index = db.replace_at_index1(selected_rows_new1.iloc[i].name, 4 + 3, 1)
    row_new = selected_rows_new1.iloc[i]
    row_new.name = new_index
    states_df = db.append_to_or_merge_with_states_df(states_df, row_new)
    db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)

selection2 = selection.query('is_rest == 1')
parameters_alignment = {'make_template_from_trial': '6_R', 'gSig_filt': (5, 5), 'max_shifts': (25, 25), 'niter_rig': 1,
                        'strides': (48, 48),'overlaps': (96, 96), 'upsample_factor_grid': 2, 'num_frames_split': 80,
                        'max_deviation_rigid': 15,'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True,
                        'border_nan': 'copy'}
selected_rows_new2 = main_alignment(selection2, parameters_alignment, dview)

for i in range(len(selection2)):
    new_index = db.replace_at_index1(selected_rows_new2.iloc[i].name, 4 + 3, 1)
    row_new = selected_rows_new2.iloc[i]
    row_new.name = new_index
    states_df = db.append_to_or_merge_with_states_df(states_df, row_new)
    db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)


#%%
selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, is_rest= is_rest,
                          decoding_v=decoding_version,
                          cropping_v=cropping_version,
                          motion_correction_v=motion_correction_version, source_extraction_v= 0, alignment_v=0)

gSig = 5
gSiz = 4 * gSig + 1
parameters_source_extraction ={'session_wise': True, 'fr': 10, 'decay_time': 0.1, 'min_corr': 0.6, 'min_pnr': 5,
                                   'p': 1, 'K': None, 'gSig': (gSig, gSig), 'gSiz': (gSiz, gSiz), 'merge_thr': 0.7, 'rf': 60,
                                   'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1, 'p_ssub': 2, 'low_rank_background': None,
                                   'nb': 0, 'nb_patch': 0, 'ssub_B': 2, 'init_iter': 2, 'ring_size_factor': 1.4,
                                   'method_init': 'corr_pnr', 'method_deconvolution': 'oasis',
                                   'update_background_components': True,
                                   'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                                   'del_duplicates': True, 'only_init': True}

corr_limits = np.linspace(0.4, 0.6, 5)
pnr_limits = np.linspace(3, 7, 5)
for j in range(len(selected_rows)):
    print(j)
    mouse_row = selected_rows.iloc[j]
    figures.plot_corr_pnr_binary(mouse_row, corr_limits, pnr_limits, parameters_source_extraction,session_wise=True)

for j in range(len(selected_rows)):
    mouse_row = selected_rows.iloc[j]
    for corr in corr_limits:
        for pnr in pnr_limits:
            parameters_source_extraction = {'session_wise': False, 'fr': 10, 'decay_time': 0.1,
                                            'min_corr': corr,
                                            'min_pnr': pnr, 'p': 1, 'K': None, 'gSig': (gSig, gSig),
                                            'gSiz': (gSiz, gSiz),
                                            'merge_thr': 0.7, 'rf': 60, 'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1,
                                            'p_ssub': 2, 'low_rank_background': None, 'nb': 0, 'nb_patch': 0,
                                            'ssub_B': 2,
                                            'init_iter': 2, 'ring_size_factor': 1.4, 'method_init': 'corr_pnr',
                                            'method_deconvolution': 'oasis', 'update_background_components': True,
                                            'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                                            'del_duplicates': True, 'only_init': True}
            mouse_row_new = main_source_extraction(mouse_row, parameters_source_extraction, dview, session_wise= True)
            states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
            db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path=backup_path)

selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, trial = 6, is_rest= is_rest,
                          cropping_v = cropping_version,
                          motion_correction_v = motion_correction_version, alignment_v= 1)

corr_limits = np.linspace(0.4, 0.6, 5)
pnr_limits = np.linspace(3, 7, 5)
version = np.arange(1,26)
for j in range(len(selected_rows)):
    mouse_row_new = selected_rows.iloc[j]
    figures.plot_multiple_contours(mouse_row_new, version, corr_limits, pnr_limits, session_wise=True)
    figures.plot_traces_multiple(mouse_row_new, version , corr_limits, pnr_limits, session_wise=True)

figure = figures.plot_multiple_contours_session_wise(selected_rows, version, corr_limits, pnr_limits)

#%% Select the row to be source extracted using current versions of cropping and motion correction

selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, is_rest= is_rest,
                          decoding_v=decoding_version,
                          cropping_v=cropping_version,
                          motion_correction_v=motion_correction_version, alignment_v=0)

gSig = 5
gSiz = 4 * gSig + 1
parameters_source_extraction ={'session_wise': False, 'fr': 10, 'decay_time': 0.1, 'min_corr': 0.6, 'min_pnr': 5,
                                   'p': 1, 'K': None, 'gSig': (gSig, gSig), 'gSiz': (gSiz, gSiz), 'merge_thr': 0.7, 'rf': 60,
                                   'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1, 'p_ssub': 2, 'low_rank_background': None,
                                   'nb': 0, 'nb_patch': 0, 'ssub_B': 2, 'init_iter': 2, 'ring_size_factor': 1.4,
                                   'method_init': 'corr_pnr', 'method_deconvolution': 'oasis',
                                   'update_background_components': True,
                                   'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                                   'del_duplicates': True, 'only_init': True}

corr_limits = np.linspace(0.4, 0.6, 5)
pnr_limits = np.linspace(3, 7, 5)
for i in range(init_trial,end_trial):
    print(i)
    selection = selected_rows.query('(trial ==' + f'{i}' + ')')
    for j in range(len(selection)):
        mouse_row = selection.iloc[j]
        figures.plot_corr_pnr_binary(mouse_row, corr_limits, pnr_limits, parameters_source_extraction,session_wise=True)

for i in range(init_trial,end_trial):
    print(i)
    selection = selected_rows.query('(trial ==' + f'{i}' + ')')
    for j in range(len(selection)):
        mouse_row = selection.iloc[j]
        for corr in corr_limits:
            for pnr in pnr_limits:
                print('Corr = ' + f'{corr}' + '_PNR = ' + f'{pnr}')
                parameters_source_extraction = {'session_wise': False, 'fr': 10, 'decay_time': 0.1,
                                                'min_corr': corr,
                                                'min_pnr': pnr, 'p': 1, 'K': None, 'gSig': (gSig, gSig),
                                                'gSiz': (gSiz, gSiz),
                                                'merge_thr': 0.7, 'rf': 60, 'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1,
                                                'p_ssub': 2, 'low_rank_background': None, 'nb': 0, 'nb_patch': 0,
                                                'ssub_B': 2,
                                                'init_iter': 2, 'ring_size_factor': 1.4, 'method_init': 'corr_pnr',
                                                'method_deconvolution': 'oasis', 'update_background_components': True,
                                                'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                                                'del_duplicates': True, 'only_init': True}
                mouse_row_new = main_source_extraction(mouse_row, parameters_source_extraction, dview)
                states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
                db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path=backup_path)

source_extraction_version = mouse_row_new.name[8]

#%%
selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, is_rest = is_rest,
                          decoding_v= decoding_version,
                          cropping_v =  cropping_version,
                          motion_correction_v=motion_correction_version,
                          source_extraction_v = source_extraction_version)

version = np.arange(1,26)

for i in range(init_trial,end_trial):
    print(i)
    selection = selected_rows.query('(trial ==' + f'{i}' + ')')
    for j in range(len(selection)):
        mouse_row_new = selection.iloc[j]
        figures.plot_multiple_contours(mouse_row_new, version, corr_limits, pnr_limits,session_wise=True)
        #figures.plot_traces_multiple(mouse_row_new, version , corr_limits, pnr_limits,session_wise=True)

#figure = figures.plot_multiple_contours_session_wise(selected_rows, version, corr_limits, pnr_limits)
figures.plot_session_contours(selected_rows, version = version , corr_array = corr_limits, pnr_array = pnr_limits)


selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, is_rest = is_rest,
                          decoding_v= 1,
                          cropping_v = 1,
                          motion_correction_v=motion_correction_version,
                          source_extraction_v = source_extraction_version)
figure = figures.plot_multiple_contours_session_wise(selected_rows, version, corr_limits, pnr_limits)

