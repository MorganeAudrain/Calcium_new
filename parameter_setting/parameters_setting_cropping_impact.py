
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 5

@author: Melisa Maidana

This script runs different cropping parameters, motion correct the cropped images using reasonable motion correction parameters that were previously selected
by using the parameters_setting_motion_correction scripts, and then run source extraction (with multiple parameters) and creates figures of the cropped
image and the extracted cells from that image. The idea is to compare the resulting source extraction neural footprint for different cropping selections.
Ideally the extracted sources should be similar. If that is the case, then all the parameter setting for every step can be run in small pieces of the image,
select the best ones, and implemented lated in the complete image.

"""

import os
import sys
import psutil
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pylab as pl

# This should be in another file. Let's leave it here for now
sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/')
sys.path.remove('/home/sebastian/Documents/calcium_imaging_analysis')

import src.configuration
import caiman as cm
import src.data_base_manipulation as db
from src.steps.cropping import run_cropper as main_cropping
from src.steps.motion_correction import run_motion_correction as main_motion_correction
from src.steps.source_extraction import run_source_extraction as main_source_extraction
import src.analysis.metrics as metrics
from caiman.source_extraction.cnmf.cnmf import load_CNMF

#Paths
analysis_states_database_path = 'references/analysis/analysis_states_database.xlsx'
backup_path = 'references/analysis/backup/'
#parameters_path = 'references/analysis/parameters_database.xlsx'

## Open thw data base with all data
states_df = db.open_analysis_states_database()
mouse = 51565
session = 1
trial = 1
is_rest = 1


# CROPPING
# Select the rows for cropping

x1_crops = np.arange(200,0,-50)
x2_crops = np.arange(350,550,50)

y1_crops = np.arange(200,0,-50)
y2_crops = np.arange(350,550,50)

n_processes = psutil.cpu_count()
cm.cluster.stop_server()
# Start a new cluster
c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                 n_processes=n_processes,  # number of process to use, if you go out of memory try to reduce this one
                                                single_thread=False)
logging.info(f'Starting cluster. n_processes = {n_processes}.')

#parametrs for motion correction
parameters_motion_correction = {'motion_correct': True, 'pw_rigid': True, 'save_movie_rig': False,
                                'gSig_filt': (5, 5), 'max_shifts': (25, 25), 'niter_rig': 1,
                                'strides': (48, 48),
                                'overlaps': (96, 96), 'upsample_factor_grid': 2, 'num_frames_split': 80,
                                'max_deviation_rigid': 15,
                                'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True, 'border_nan': 'copy'}


#parameters for source extraction
gSig = 5
gSiz = 4 * gSig + 1
corr_limits = np.linspace(0.4, 0.6, 5)
pnr_limits = np.linspace(3, 7, 5)
cropping_v = np.zeros(5)
motion_correction_v = np.zeros(5)

selected_rows = db.select(states_df,'cropping', mouse = mouse, session = session, trial = trial , is_rest = is_rest)
mouse_row = selected_rows.iloc[0]
for kk in range(4):
    cropping_interval = [x1_crops[kk], x2_crops[kk], y1_crops[kk], y2_crops[kk]]
    parameters_cropping = {'crop_spatial': True, 'cropping_points_spatial': cropping_interval,
                           'crop_temporal': False, 'cropping_points_temporal': []}
    mouse_row = main_cropping(mouse_row, parameters_cropping)
    cropping_v[kk] = mouse_row.name[5]
    states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row)
    db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)


states_df = db.open_analysis_states_database()
for kk in range(4):
    selected_rows = db.select(states_df, 'motion_correction', 56165, cropping_v = cropping_v[kk])
    mouse_row = selected_rows.iloc[0]
    mouse_row_new = main_motion_correction(mouse_row, parameters_motion_correction, dview)
    mouse_row_new = metrics.get_metrics_motion_correction(mouse_row_new, crispness=True)
    states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
    db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)
    motion_correction_v[kk]=mouse_row_new.name[6]


states_df = db.open_analysis_states_database()
for ii in range(corr_limits.shape[0]):
    for jj in range(pnr_limits.shape[0]):
        parameters_source_extraction = {'session_wise': False, 'fr': 10, 'decay_time': 0.1,
                                        'min_corr': corr_limits[ii],
                                        'min_pnr': pnr_limits[jj], 'p': 1, 'K': None, 'gSig': (gSig, gSig),
                                        'gSiz': (gSiz, gSiz),
                                        'merge_thr': 0.7, 'rf': 60, 'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1,
                                        'p_ssub': 2, 'low_rank_background': None, 'nb': 0, 'nb_patch': 0,
                                        'ssub_B': 2,
                                        'init_iter': 2, 'ring_size_factor': 1.4, 'method_init': 'corr_pnr',
                                        'method_deconvolution': 'oasis', 'update_background_components': True,
                                        'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                                        'del_duplicates': True, 'only_init': True}
        for kk in range(4):
            selected_rows = db.select(states_df, 'source_extraction', 56165, cropping_v = cropping_v[kk])
            mouse_row = selected_rows.iloc[0]
            mouse_row_new = main_source_extraction(mouse_row, parameters_source_extraction, dview)
            states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
            db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path=backup_path)


states_df = db.open_analysis_states_database()
for ii in range(corr_limits.shape[0]):
    for jj in range(pnr_limits.shape[0]):
        figure, axes = plt.subplots(4, 3, figsize=(50, 30))
        version = ii * pnr_limits.shape[0] + jj +1
        for kk in range(4):
            selected_rows = db.select(states_df, 'component_evaluation', 56165, cropping_v=cropping_v[kk], motion_correction_v = 1, source_extraction_v= version)
            mouse_row = selected_rows.iloc[0]

            decoding_output = mouse_row['decoding_output']
            decoded_file = eval(decoding_output)['main']
            m = cm.load(decoded_file)
            axes[kk,0].imshow(m[0, :, :], cmap='gray')
            cropping_interval = [x1_crops[kk], x2_crops[kk], y1_crops[kk], y2_crops[kk]]
            [x_, _x, y_, _y] = cropping_interval
            rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='r', linestyle='--', linewidth = 3)
            axes[kk,0].add_patch(rect)

            output_cropping = mouse_row['cropping_output']
            cropped_file = eval(output_cropping)['main']
            m = cm.load(cropped_file)
            axes[kk,1].imshow(m[0, :, :], cmap='gray')

            output_source_extraction = eval(mouse_row['source_extraction_output'])
            cnm_file_path = output_source_extraction['main']
            cnm = load_CNMF(db.get_file(cnm_file_path))
            corr_path = output_source_extraction['meta']['corr']['main']
            cn_filter = np.load(db.get_file(corr_path))
            axes[kk, 2].imshow(cn_filter)
            coordinates = cm.utils.visualization.get_contours(cnm.estimates.A, np.shape(cn_filter), 0.2, 'max')
            for c in coordinates:
                v = c['coordinates']
                c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                             np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
                axes[kk, 2].plot(*v.T, c='w',linewidth=3)

        fig_dir ='/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/cropping/meta/figures/cropping_inicialization/'
        fig_name = fig_dir +  db.create_file_name(2,mouse_row.name) + '_corr_' + f'{round(corr_limits[ii],1)}' + '_pnr_' + f'{round(pnr_limits[jj])}' + '.png'
        figure.savefig(fig_name)
