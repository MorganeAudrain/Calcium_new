#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 09:19:20 2019

@author: Melisa
"""

import os
import sys
import psutil
import logging

# This should be in another file. Let's leave it here for now
sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/')
sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/steps/')
sys.path.remove('/home/sebastian/Documents/calcium_imaging_analysis')

#%% ENVIRONMENT VARIABLES
os.environ['PROJECT_DIR_LOCAL'] = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/'
os.environ['PROJECT_DIR_SERVER'] = '/scratch/mmaidana/calcium_imaging_analysis/'
os.environ['CAIMAN_DIR_LOCAL'] = '/home/sebastian/CaImAn/'
os.environ['CAIMAN_DIR_SERVER'] ='/scratch/mamaidana/CaImAn/'
os.environ['CAIMAN_ENV_SERVER'] = '/scratch/mmaidana/anaconda3/envs/caiman/bin/python'

os.environ['LOCAL_USER'] = 'sebastian'
os.environ['SERVER_USER'] = 'mmaidana'
os.environ['SERVER_HOSTNAME'] = 'cn76'
os.environ['ANALYST'] = 'Meli'

#%% PROCESSING
os.environ['LOCAL'] = str((os.getlogin() == os.environ['LOCAL_USER']))
os.environ['SERVER'] = str(not(eval(os.environ['LOCAL'])))
os.environ['PROJECT_DIR'] = os.environ['PROJECT_DIR_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['PROJECT_DIR_SERVER']
os.environ['CAIMAN_DIR'] = os.environ['CAIMAN_DIR_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['CAIMAN_DIR_SERVER']
#%%
import caiman as cm
import src.data_base_manipulation as db
from src.steps.decoding import run_decoder as main_decoding
from src.steps.cropping import run_cropper as main_cropping
from src.steps.cropping import cropping_interval, plot_movie_frame, plot_movie_frame_cropped
from src.steps.motion_correction import run_motion_correction as main_motion_correction
from src.steps.source_extraction import run_source_extraction as main_source_extraction
from src.steps.component_evaluation import run_component_evaluation as main_component_evaluation
import src.analysis_files_manipulation as fm
import src.analysis.metrics as metrics

#%%

# Paths
analysis_states_database_path = 'references/analysis/analysis_states_database.xlsx'
backup_path = 'references/analysis/backup/'
parameters_path = 'references/analysis/parameters_database.xlsx'

## Open thw data base with all data
states_df = db.open_analysis_states_database()
## Select all the data corresponding to a particular mouse. Ex: 56165

selected_rows = db.select('decoding',56165)

parameters_cropping= {'crop_spatial': True, 'cropping_points_spatial': [80, 450, 210, 680],
                      'crop_temporal': False, 'cropping_points_temporal': []}

parameters_motion_correction = {'motion_correct': True, 'pw_rigid': True, 'save_movie_rig': False,
              'gSig_filt': (7, 7), 'max_shifts': (25, 25), 'niter_rig': 1, 'strides': (96, 96),
              'overlaps': (48, 48), 'upsample_factor_grid': 2, 'num_frames_split': 80, 'max_deviation_rigid': 15,
              'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True, 'border_nan': 'copy'}

parameters_source_extraction ={'session_wise': False, 'fr': 10, 'decay_time': 0.1, 'min_corr': 0.77, 'min_pnr': 6.6,
                               'p': 1, 'K': None, 'gSig': (5, 5), 'gSiz': (20, 20), 'merge_thr': 0.7, 'rf': 60,
                               'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1, 'p_ssub': 2, 'low_rank_background': None,
                               'nb': 0, 'nb_patch': 0, 'ssub_B': 2, 'init_iter': 2, 'ring_size_factor': 1.4,
                               'method_init': 'corr_pnr', 'method_deconvolution': 'oasis',
                               'update_background_components': True,
                               'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                               'del_duplicates': True, 'only_init': True}


min_SNR = 3           # adaptive way to set threshold on the transient size
r_values_min = 0.85    # threshold on space consistency (if you lower more components
#                        will be accepted, potentially with worst quality)
parameters_component_evaluation = {'min_SNR': min_SNR,
                                   'rval_thr': r_values_min,
                                   'use_cnn': False}

#%%
for i in range(0, len(selected_rows)):

    # Get the row from the selected rows as a series using simple indexing
    row = selected_rows.iloc[i]
    index=row.name
    # Get the index from the row
    row = main_decoding(row)
    print('Decoding for mouse' + str(index[0]) + 'session' + str(index[1]) + 'trial' + str(index[2]) )
    states_df = db.append_to_or_merge_with_states_df(states_df, row)
    db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)

    row = main_cropping(row,parameters_cropping)
    #upload_to_server_cropped_movie(index,row)
    print('Cropping for mouse' + str(index[0]) + 'session' + str(index[1]) + 'trial' + str(index[2]) )
    n_processes = psutil.cpu_count()
    cm.cluster.stop_server()
    # Start a new cluster
    c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                      n_processes=n_processes,  # number of process to use, if you go out of memory try to reduce this one
                                                      single_thread=False)
    logging.info(f'Starting cluster. n_processes = {n_processes}.')

    row=main_motion_correction(row,parameters_motion_correction,dview)
    print('MotionCorrection for mouse' + str(index[0]) + 'session' + str(index[1]) + 'trial' + str(index[2]) )


    # Compute metrics for quality assesment in motion corrected movies'crispness'
    row = metrics.get_metrics_motion_correction(row, crispness = True)


    # Create source extraction images in advance:

    #logging.info(f'{index} Creating corr and pnr images in advance')
    #index, row = fm.get_corr_pnr(index, row)
    #logging.info(f'{index} Created corr and pnr images')

    main_source_extraction(row,parameters_source_extraction,dview)
    print('SourceExtraction for mouse' + str(index[0]) + 'session' + str(index[1]) + 'trial' + str(index[2]) )

    cm.stop_server(dview=dview)
    main_component_evaluation(index,row,parameters_component_evaluation)
    print('ComponentEvaluation for mouse' + str(index[0]) + 'session' + str(index[1]) + 'trial' + str(index[2]) )
    states_df = db.append_to_or_merge_with_states_df(states_df, row)
    db.save_analysis_states_database(states_df, path = analysis_states_database_path,backup_path=backup_path)
