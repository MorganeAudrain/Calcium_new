#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 09:19:20 2019

@author: Melisa

This script is designed to explore the effect of different source extraction parameters in the final output of the algorithm.\

Three main parameters are explores: gSig (typical neuron size), minimal pnr and minimal correlation (seeds or initial
conditions for the CNMF-E algorithm).

It produces different kind of plots where visual inspection of parameter selection is easy to evaluate :




"""
import sys
import psutil
import logging
import numpy as np

# This should be in another file. Let's leave it here for now
#sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/')
#sys.path.remove('/home/sebastian/Documents/calcium_imaging_analysis')

import configuration
import caiman as cm
import data_base_manipulation as db

from steps.source_extraction import run_source_extraction as main_source_extraction
import analysis.figures as figures
import analysis.metrics as metrics

# Paths to data base and back up
analysis_states_database_path = 'analysis_states_database.xlsx'
backup_path = 'data/'
parameters_path = 'parameters_database.xlsx'

#load data base
states_df = db.open_analysis_states_database()
#define the experimental details
mouse = 32364
session = 1
trial = 10
is_rest = None

#define previus steps analysis versions that are desired to explore in source extraction
cropping_version = 1
motion_correction_version = 1

## use now until conexion with the server is back (this is to load the data base directly from the computer)
#import pandas as pd
#import src.paths as paths
#states_df = pd.read_excel(analysis_states_database_path, dtype={'date': 'str', 'time': 'str'}).set_index(paths.multi_index_structure)

#select states for source extraction
selected_rows = db.select(states_df,'source_extraction', mouse = mouse, session = session, trial = trial, is_rest = is_rest,
                          cropping_v =  cropping_version, motion_correction_v = motion_correction_version)

#for testing parameters select one of the states
mouse_row = selected_rows.iloc[0]

#%%For visualization: plot different gSig size in corr and pnr images

#define the values of interest for gSig_size (remember this is not the same as for motion correction) and this is related
#to the tipical neuronal size and to the ring model for the background in the CNMF-E pipeline.


gSig_size = np.arange(1,10,1)
corr = np.zeros(gSig_size.shape)
pnr = np.zeros(gSig_size.shape)
comb = np.zeros(gSig_size.shape)

ii=0
for gSig in gSig_size:
    gSiz = 4*gSig+1
    parameters_source_extraction ={'session_wise': False, 'fr': 10, 'decay_time': 0.1, 'min_corr': 0.95, 'min_pnr': 10,
                                   'p': 1, 'K': None, 'gSig': (gSig, gSig), 'gSiz': (gSiz, gSiz), 'merge_thr': 0.7, 'rf': 60,
                                   'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1, 'p_ssub': 2, 'low_rank_background': None,
                                   'nb': 0, 'nb_patch': 0, 'ssub_B': 2, 'init_iter': 2, 'ring_size_factor': 1.4,
                                   'method_init': 'corr_pnr', 'method_deconvolution': 'oasis',
                                   'update_background_components': True,
                                   'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                                   'del_duplicates': True, 'only_init': True}

    comb[ii], corr[ii], pnr[ii] = metrics.select_corr_pnr_threshold(mouse_row, parameters_source_extraction)
    ii =ii + 1
    figures.plot_corr_pnr(mouse_row,parameters_source_extraction)

#%%
## Now we explore selection of min_corr and min_pnr. For that we selected one value of gSig that was considered reasonable.

# From now on, corr_min and pnr_min will be the most relevant parameters to tuned, as they are the seeds of the algorithm.
# From the output of this exploration, it is visible how the inicial conditions affects the final output of the algorithm.


# selected fixed gSig and gSiz
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


corr_hist,pos_corr, pnr_hist, pos_pnr = metrics.create_corr_pnr_histogram(mouse_row,parameters_source_extraction)
histogram_dir = 'data/interim/source_extraction/trial_wise/meta/'

histogram_corr = figures.plot_histogram(pos_corr[:-1],corr_hist, title = 'Correlation Histogram', xlabel= 'Correlation', ylabel= 'Prob of occurrence')
histogram_corr_name= histogram_dir + f'figures/corr_pnr/histogram/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}_corr.png'
histogram_corr.savefig(histogram_corr_name)
histogram_pnr = figures.plot_histogram(pos_pnr[:-1],pnr_hist, title = 'PNR Histogram', xlabel= 'PNR', ylabel= 'Prob of occurrence')
histogram_pnr_name= histogram_dir + f'figures/corr_pnr/histogram/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}_pnr.png'
histogram_pnr.savefig(histogram_pnr_name)


## Select a set of parameters and plot the binary corr, pnr and combined image to explore visualy different seed selections.
corr_limits = np.linspace(pos_corr[40],pos_corr[40]+0.2,5)
pnr_limits = np.linspace(pos_pnr[5],pos_pnr[5]+10,5)
figures.plot_corr_pnr_binary(mouse_row, corr_limits, pnr_limits, parameters_source_extraction)


#%% Now running source_extraction in the selected parameters and evaluation the result.
# First evaluation is visual inspection of contours
# Second evaluation is visual inspection of calcium traces in time
# Thrird evaluation is component evaluation by using step 5.

#inicialize a cluster
n_processes = psutil.cpu_count()
cm.cluster.stop_server()
# Start a new cluster
c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                 n_processes=n_processes,  # number of process to use, if you go out of memory try to reduce this one
                                                single_thread=False)

logging.info(f'Starting cluster. n_processes = {n_processes}.')

#select the range of min_corr, min_pnr to explore, and set gSig and gSiz. Preferably, work with the same ones as before
# to check the effects of the seeds and filter size in the performance of the source extraction algorithm.

#corr_limits = np.linspace(pos_corr[40],pos_corr[40]+0.2,5)
#pnr_limits = np.linspace(pos_pnr[5],pos_pnr[5]+10,5)
#gSig = 5
#gSiz = 4 * gSig + 1

version = np.zeros((len(corr_limits)*len(pnr_limits)))

for ii in range(corr_limits.shape[0]):
    for jj in range(pnr_limits.shape[0]):
        parameters_source_extraction ={'session_wise': False, 'fr': 10, 'decay_time': 0.1, 'min_corr': corr_limits[ii],
                                       'min_pnr': pnr_limits[jj],'p': 1, 'K': None, 'gSig': (gSig, gSig), 'gSiz': (gSiz, gSiz),
                                       'merge_thr': 0.7, 'rf': 60, 'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1,
                                       'p_ssub': 2, 'low_rank_background': None, 'nb': 0, 'nb_patch': 0, 'ssub_B': 2,
                                       'init_iter': 2, 'ring_size_factor': 1.4, 'method_init': 'corr_pnr',
                                       'method_deconvolution': 'oasis', 'update_background_components': True,
                                        'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                                        'del_duplicates': True, 'only_init': True}
        mouse_row_new = main_source_extraction(mouse_row, parameters_source_extraction, dview)
        states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
        db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)
        #save the version number for furhter plotting
        version[ii*len(pnr_limits)+jj] = mouse_row_new.name[8]

## plottin. This funcion  shoul be improved to be given a list of corr and pnr values and search in the data base that
#specific values, insted of going all over the versions values...

figures.plot_multiple_contours(mouse_row_new, version, corr_limits, pnr_limits)
figures.plot_traces_multiple(mouse_row_new, version , corr_limits, pnr_limits)

cm.stop_server(dview=dview)


#%% So far this can be run for each mouse, session, trial and resting condition with out possibility of generalizing.
# It is useful is this script is run for different of those, so it will be visible how different pnr and corr parameters can
# not be directly used in different sessions or different trials.

# for the moments, add a line here that saves the selected parameters for source extraction for each particular mouse,
# session, trial and resting condtion, that should be done manually for each, and refer to
# parameter_setting_source_extraction_session_wise and parameters_settion_source_extraction_session_wise_equalized
# for generalization of parameters selection.

