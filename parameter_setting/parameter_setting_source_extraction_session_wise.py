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
init_trial = 10
end_trial = 10
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

for i in range(init_trial,end_trial):
    selection = selected_rows.query('(trial ==' + f'{i}' + ')')
    for j in range(len(selection)):
        mouse_row = selection.iloc[j]
        mouse_row = main_decoding(mouse_row)
        states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row)
        db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)

decoding_version = mouse_row.name[4]
#%% Run cropping for the already decoded group

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

for i in range(len(selection1)):
    new_index = db.replace_at_index1(selected_rows_new2.iloc[i].name, 4 + 3, 1)
    row_new = selected_rows_new2.iloc[i]
    row_new.name = new_index
    states_df = db.append_to_or_merge_with_states_df(states_df, row_new)
    db.save_analysis_states_database(states_df, analysis_states_database_path, backup_path)


#%%
selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, trial = 6, is_rest= is_rest,
                          cropping_v = cropping_version,
                          motion_correction_v = motion_correction_version, alignment_v= 1, source_extraction_v= 4 )

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
            parameters_source_extraction = {'session_wise': True, 'fr': 10, 'decay_time': 0.1,
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
    #figures.plot_multiple_contours(mouse_row_new, version, corr_limits, pnr_limits, session_wise=True)
    figures.plot_traces_multiple(mouse_row_new, version , corr_limits, pnr_limits, session_wise=True)


#%%
motion_correction_version = 1
cropping_version = 1
selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, trial = 6, is_rest= is_rest,
                          cropping_v = cropping_version,
                          motion_correction_v = motion_correction_version, alignment_v= 0, source_extraction_v= 1 )

row = selected_rows.iloc[1]

#input_mmap_file_path = eval(row.loc['alignment_output'])['main']
input_mmap_file_path = eval(row.loc['motion_correction_output'])['main']
Yr, dims, T = cm.load_memmap(input_mmap_file_path)
# logging.debug(f'{index} Loaded movie. dims = {dims}, T = {T}.')
images = Yr.T.reshape((T,) + dims, order='F')
images = cm.movie(images)

output = eval(row.loc['source_extraction_output'])
cnm_file_path = output['main']
cnm = load_CNMF(db.get_file(cnm_file_path))
W, b0 = cm.source_extraction.cnmf.initialization.compute_W(Yr, cnm.estimates.A.toarray(), cnm.estimates.C, cnm.estimates.dims, 1.4 *5,ssub=2)
cnm.estimates.W = W
cnm.estimates.b0 = b0
#movie_dir = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/processed/movies/'
#file_name = db.create_file_name(5,row.name)
#cnm.estimates.play_movie(cnm.estimates, images, movie_name= movie_dir + file_name + '.avi')

frame_range=slice(None, None, None)
Y_rec = cnm.estimates.A.dot(cnm.estimates.C[:, frame_range])
Y_rec = Y_rec.reshape(dims + (-1,), order='F')
Y_rec = Y_rec.transpose([2, 0, 1])
Y_rec = cm.movie(Y_rec)

#mov = cm.concatenate((images, Y_rec), axis=2)
#mov.play()

ssub_B = int(round(np.sqrt(np.prod(dims) / W.shape[0])))
B = images[frame_range].reshape((-1, np.prod(dims)), order='F').T - \
    cnm.estimates.A.dot(cnm.estimates.C[:, frame_range])
if ssub_B == 1:
    B = b0[:, None] + W.dot(B - b0[:, None])
else:
    B = b0[:, None] + (np.repeat(np.repeat(W.dot(
        downscale(B.reshape(dims + (B.shape[-1],), order='F'),
                    (ssub_B, ssub_B, 1)).reshape((-1, B.shape[-1]), order='F') -
        downscale(b0.reshape(dims, order='F'),
                  (ssub_B, ssub_B)).reshape((-1, 1), order='F'))
                                                  .reshape(
        ((dims[0] - 1) // ssub_B + 1, (dims[1] - 1) // ssub_B + 1, -1), order='F'),
                                                ssub_B, 0), ssub_B, 1)[:dims[0], :dims[1]].reshape(
        (-1, B.shape[-1]), order='F'))
B = B.reshape(dims + (-1,), order='F').transpose([2, 0, 1])


Y_res = images[frame_range] - Y_rec - B

mov = cm.concatenate((images, Y_rec), axis=2)



mov = cm.concatenate((images, images), axis=2)


#%% Select the row to be source extracted using current versions of cropping and motion correction

selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, is_rest= is_rest,
                          cropping_v = cropping_version,
                          motion_correction_v = motion_correction_version)

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
selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, is_rest = is_rest, cropping_v =  cropping_version,
                          motion_correction_v=motion_correction_version, source_extraction_v = source_extraction_version)
version = np.arange(1,26)

for i in range(init_trial,end_trial):
    print(i)
    selection = selected_rows.query('(trial ==' + f'{i}' + ')')
    for j in range(len(selection)):
        mouse_row_new = selection.iloc[j]
        figures.plot_multiple_contours(mouse_row_new, version, corr_limits, pnr_limits,session_wise=True)
        figures.plot_traces_multiple(mouse_row_new, version , corr_limits, pnr_limits,session_wise=True)

figure = figures.plot_multiple_contours_session_wise(selected_rows, version, corr_limits, pnr_limits)
figures.plot_session_contours(selected_rows, version = version , corr_array = corr_limits, pnr_array = pnr_limits)

#%% Evaluate components for trial 1

source_extraction_v_array = np.arange(1,26)

min_SNR_array =np.arange(3,7,1)
r_values_min_array = [0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95]

for trial in range(init_trial,end_trial):
    for kk in range(len(source_extraction_v_array)):
        for ii in range(len(min_SNR_array)):
            for jj in range(len(r_values_min_array)):
                min_SNR = min_SNR_array[ii]
                r_values_min = r_values_min_array[jj]
                selected_row= db.select(states_df, 'component_evaluation', mouse = mouse_number, trial = trial,
                                        cropping_v = cropping_version, motion_correction_v=motion_correction_version,
                                     source_extraction_v= source_extraction_v_array[kk])

                mouse_row = selected_row.iloc[0]
                parameters_component_evaluation = {'min_SNR': min_SNR,
                                                   'rval_thr': r_values_min,
                                                   'use_cnn': False}
                mouse_row_new = main_component_evaluation(mouse_row, parameters_component_evaluation)
                states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
                db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)

#%%
selected_rows = db.select(states_df,'component_evaluation',mouse = mouse_number, cropping_v =  cropping_version,
                          motion_correction_v = motion_correction_version, source_extraction_v = source_extraction_version,
                          component_evaluation_v= 11)

figures.plot_multiple_contours_session_wise_evaluated(selected_rows)


#%% on development!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

component_evaluation_v_array = np.arange(0,len(min_SNR_array)*len(r_values_min_array))

number_cell5 = np.zeros((len(source_extraction_v_array),len(component_evaluation_v_array)))
fraction5 = np.zeros((len(source_extraction_v_array),len(component_evaluation_v_array)))

for kk in range(1,len(source_extraction_v_array)):
    for ll in range(1,len(component_evaluation_v_array)):
        selected_row = db.select(states_df, 'component_evaluation', 56165, trial = 5, cropping_v=1, motion_correction_v=1,
                                 source_extraction_v=source_extraction_v_array[kk], component_evaluation_v = component_evaluation_v_array[ll])
        mouse_row = selected_row.iloc[0]
        output_component_evaluation = eval(mouse_row.loc['component_evaluation_output'])
        cnm_file_path = output_component_evaluation['main']
        cnm = load_CNMF(db.get_file(cnm_file_path))
        number_cell5[kk-1][ll-1] = cnm.estimates.A.shape[1]
        fraction5[kk-1][ll-1] = len(cnm.estimates.idx_components) / number_cell5[kk-1][ll-1]

list1 = []
list2 = []
list3 = []
list4 = []

for kk in range(1,len(source_extraction_v_array)):
    for ll in range(1,len(component_evaluation_v_array)):
        list1.append(number_cell[kk-1][ll-1])
        list2.append(1-fraction[kk-1][ll-1])
        list3.append(number_cell5[kk - 1][ll - 1])
        list4.append(1-fraction5[kk-1][ll-1])

product = np.arange(0,len(list1))
false_positive = np.zeros((len(list1)))
false_positive_next = np.zeros((len(list1)))
for ii in range(len(product)-1):
    product[ii] = list3[ii] * list2[ii]
    false_positive[ii] = list4[ii]
    false_positive_next[ii] = list4[ii+1]



file_name_number = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/component_evaluation/session_wise/meta/metrics/' + db.create_file_name(5,mouse_row.name) + '_number'
np.save(file_name_number,number_cell5)
file_name_fraction = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/component_evaluation/session_wise/meta/metrics/' + db.create_file_name(5,mouse_row.name) + '_fraction'
np.save(file_name_fraction,fraction5)




#%% Working with matching!!!!!!

one_version = 13
selected_rows = db.select(states_df,'source_extraction',56165, cropping_v =  1,
                          motion_correction_v=1, source_extraction_v =one_version)

A_list = []
A_pixel = []
A_dims = []
A_components=[]
for i in range(1,3):
    row= selected_rows.iloc[i]
    source_extraction_output = eval(row.loc['source_extraction_output'])
    input_hdf5_file_path = source_extraction_output['main']
    cnm = load_CNMF(input_hdf5_file_path)
    corr_path = source_extraction_output['meta']['corr']['main']
    cn_filter = np.load(db.get_file(corr_path))
    A_dims.append(cn_filter.shape)
    A_pixel.append(cnm.estimates.A.shape[0])
    A_components.append(cnm.estimates.A.shape[1])
    A_list.append(cnm.estimates.A)

new_dims = A_dims[np.argmin(A_pixel)]
new_pixel = min(A_pixel)
new_A_list = []
for i in range(0,5):
    current_list = A_list[i]
    new_A_list.append(current_list[:new_pixel])

spatial_union, assignments, match = register_multisession(A=new_A_list, dims=new_dims)




figure, axes = plt.subplots(figsize=(15, 15))
coordinates = cm.utils.visualization.get_contours(spatial_union, new_dims, 0.2, 'max')

coordinates5 = coordinates[146:150]

for i in range(5):
    axes.imshow(cn_filter[:new_dims[0]][:new_dims[1]])
    for c in coordinates5:
        v = c['coordinates']
        c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                     np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
        axes.plot(*v.T, c='w')



#%%

cm.stop_server(dview=dview)