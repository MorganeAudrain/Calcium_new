#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author:Sebastian, Casper,  Melisa Maidana

This module will concentrate all the functions related to quality measurements for the pipeline and also make some ploting
for comparing those measures.


"""


import os
import logging
import pickle
import numpy as np
import datetime
import caiman as cm
import pylab as pl
from caiman.motion_correction import MotionCorrect


import analysis.analysis_files_manipulation as fm

import scipy
import cv2

def get_metrics_motion_correction(row, crispness=False, local_correlations=False, correlations=False,
                optical_flow=False):
    '''
    This is a wrapper function to compute (a selection of) the metrics provided
    by CaImAn for motion correction.

    input -> row : dictionary with all relevant file-paths
             crispness : bool variable to indicate whether crispness is supposed to be computed
             local_correlations ->  bool variable to indicate whether local_correlations is supposed to be computed
             correlations - >  bool variable to indicate whether correlations is supposed to be computed
             optical_flow ->  bool variable to indicate whether optical_flow is supposed to be computed

    output -> row_local : dictionary with new outputs directions

    '''
    row_local = row.copy()
    index = row_local.name
    # Get the parameters, motion correction output and cropping output of this row
    parameters = eval(row_local.loc['motion_correction_parameters'])
    output = eval(row_local.loc['motion_correction_output'])
    cropping_output = eval(row_local.loc['cropping_output'])
    # Get the metrics file path
    metrics_pkl_file_path = output['meta']['metrics']['other']
    # Load the already available metrics
    with open(metrics_pkl_file_path, 'rb') as f:
        try:
            meta_dict = pickle.load(f)
        except:
            meta_dict = {}

    # ORIGINAL MOVIE
    logging.info(f'{index} Computing metrics for original movie')
    t0 = datetime.datetime.today()
    fname_orig = cropping_output['main']
    tmpl_orig, crispness_orig, crispness_corr_orig, correlations_orig, img_corr_orig, flows_orig, norms_orig = compute_metrics_motion_correction(
        fname_orig, swap_dim=False, winsize=100, play_flow=False,
        resize_fact_flow=.2, one_photon=True, crispness=crispness,
        correlations=correlations, local_correlations=local_correlations,
        optical_flow=optical_flow)
    dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
    output['meta']['metrics']['original'] = {
        'crispness': crispness_orig,
        'crispness_corr': crispness_corr_orig
    }
    meta_dict['original'] = db.remove_None_from_dict({
        'correlations': correlations_orig,
        'local_correlations': img_corr_orig,
        'flows': flows_orig,
        'norms': norms_orig})
    output['meta']['duration']['metrics_orig'] = dt
    logging.info(f'{index} Computed metrics for original movie. dt = {dt} min')

    # RIGID MOVIE
    if not parameters['pw_rigid'] or (parameters['pw_rigid'] and 'alternate' in output):
        logging.info(f'{index} Computing metrics for rigid movie')
        t0 = datetime.datetime.today()
        fname_rig = output['main'] if not parameters['pw_rigid'] else output['alternate']
        tmpl_rig, crispness_rig, crispness_corr_rig, correlations_rig, img_corr_rig, flows_rig, norms_rig = compute_metrics_motion_correction(
            fname_rig, swap_dim=False, winsize=100, play_flow=False,
            resize_fact_flow=.2, one_photon=True, crispness=crispness,
            correlations=correlations, local_correlations=local_correlations,
            optical_flow=optical_flow)
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        output['meta']['metrics']['rigid'] = {
            'crispness': crispness_rig,
            'crispness_corr': crispness_corr_rig
        }
        meta_dict['rigid'] = db.remove_None_from_dict({
            'correlations': correlations_rig,
            'local_correlations': img_corr_rig,
            'flows': flows_rig,
            'norms': norms_rig})
        output['meta']['duration']['metrics_rig'] = dt
        logging.info(f'{index} Computed metrics for rigid movie. dt = {dt} min')

    if parameters['pw_rigid']:
        logging.info(f'{index} Computing metrics for pw-rigid movie')
        t0 = datetime.datetime.today()
        fname_els = output['main']
        tmpl_els, crispness_els, crispness_corr_els, correlations_els, img_corr_els, flows_els, norms_els = compute_metrics_motion_correction(
            fname_els, swap_dim=False,
            resize_fact_flow=.2, one_photon=True, crispness=crispness,
            correlations=correlations, local_correlations=local_correlations,
            optical_flow=optical_flow)
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        output['meta']['metrics']['pw_rigid'] = {
            'crispness': crispness_els,
            'crispness_corr': crispness_corr_els
        }
        meta_dict['pw_rigid'] = db.remove_None_from_dict({
            'correlations': correlations_els,
            'local_correlations': img_corr_els,
            'flows': flows_els,
            'norms': norms_els})
        output['meta']['duration']['metrics_els'] = dt
        logging.info(f'{index} Computed metrics for pw-rigid movie. dt = {dt} min')

        # Save the metrics in a pkl file
    logging.info(f'{index} Saving metrics')
    with open(metrics_pkl_file_path, 'wb') as f:
        pickle.dump(meta_dict, f)
    logging.info(f'{index} Saved metrics')

    row_local.loc['motion_correction_output'] = str(output)

    return row_local


def compute_metrics_motion_correction(file_name, swap_dim, pyr_scale=.5, levels=3,
                          winsize=100, iterations=15, poly_n=5, poly_sigma=1.2 / 5, flags=0,
                          play_flow=False, resize_fact_flow=.2, template=None, save_npz=False,
                          one_photon=True, crispness=True, correlations=True, local_correlations=True,
                          optical_flow=True):
    '''
    This function is actually copied from the CaImAn packages and edited for use in this calcium
    imaging analysis pipeline. It contained some abnormalities that we wanted to avoid.
    '''
    # Logic
    if crispness: local_correlations = True

    # Load the movie
    m = cm.load(file_name)
    vmin, vmax = -1, 1

    # Check the movie for NaN's which may cause problems
    if np.sum(np.isnan(m)) > 0:
        logging.info(m.shape)
        logging.warning('Movie contains NaN')
        raise Exception('Movie contains NaN')

    if template is None:
        tmpl = cm.motion_correction.bin_median(m)
    else:
        tmpl = template

    if correlations:
        logging.debug('Computing correlations')
        t0 = datetime.datetime.today()
        correlations = []
        count = 0
        if one_photon:
            m_compute = m - np.min(m)
        for fr in m_compute:
            if count % 100 == 0:
                logging.debug(f'Frame {count}')
            count += 1
            correlations.append(scipy.stats.pearsonr(
                fr.flatten(), tmpl.flatten())[0])
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        logging.debug(f'Computed correlations. dt = {dt} min')
    else:
        correlations = None

    if local_correlations:
        logging.debug('Computing local correlations')
        t0 = datetime.datetime.today()
        img_corr = m.local_correlations(eight_neighbours=True, swap_dim=swap_dim)
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        logging.debug(f'Computed local correlations. dt = {dt} min')
    else:
        img_corr = None

    if crispness:
        logging.debug('Computing crispness')
        t0 = datetime.datetime.today()
        smoothness = np.sqrt(
            np.sum(np.sum(np.array(np.gradient(np.mean(m, 0))) ** 2, 0)))
        smoothness_corr = np.sqrt(
            np.sum(np.sum(np.array(np.gradient(img_corr)) ** 2, 0)))
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        logging.debug(
            f'Computed crispness. dt = {dt} min. Crispness = {smoothness}, crispness corr = {smoothness_corr}.')
    else:
        smoothness = None

    if optical_flow:
        logging.debug('Computing optical flow')
        t0 = datetime.datetime.today()
        m = m.resize(1, 1, resize_fact_flow)
        norms = []
        flows = []
        count = 0
        for fr in m:
            if count % 100 == 0:
                logging.debug(count)

            count += 1
            flow = cv2.calcOpticalFlowFarneback(
                tmpl, fr, None, pyr_scale, levels, winsize, iterations, poly_n, poly_sigma, flags)

            if play_flow:
                pl.subplot(1, 3, 1)
                pl.cla()
                pl.imshow(fr, vmin=0, vmax=300, cmap='gray')
                pl.title('movie')
                pl.subplot(1, 3, 3)
                pl.cla()
                pl.imshow(flow[:, :, 1], vmin=vmin, vmax=vmax)
                pl.title('y_flow')

                pl.subplot(1, 3, 2)
                pl.cla()
                pl.imshow(flow[:, :, 0], vmin=vmin, vmax=vmax)
                pl.title('x_flow')
                pl.pause(.05)

            n = np.linalg.norm(flow)
            flows.append(flow)
            norms.append(n)
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        logging.debug(f'Computed optical flow. dt = {dt} min')
    else:
        flows = norms = None

    if save_npz:
        logging.debug('Saving metrics in .npz format')
        np.savez(file_name[:-4] + '_metrics', flows=flows, norms=norms, correlations=correlations, smoothness=smoothness,
                 tmpl=tmpl, smoothness_corr=smoothness_corr, img_corr=img_corr)
        logging.debug('Saved metrics in .npz format')

    return tmpl, smoothness, smoothness_corr, correlations, img_corr, flows, norms

def compare_crispness(selected_rows = None):

    total_states_number = len(selected_rows)
    crispness_mean = np.zeros(total_states_number-1)
    crispness_corr = np.zeros(total_states_number-1)
    crispness_mean_original = np.zeros(total_states_number-1)
    crispness_corr_original = np.zeros(total_states_number-1)

    #for ii in range(0,total_states_number-1):
    for ii in range(0,total_states_number-1):
        currect_row = selected_rows.iloc[ii+1]
        output_dic = eval(currect_row['motion_correction_output'])
        crispness_mean_original[ii] = output_dic['meta']['metrics']['original']['crispness']
        crispness_corr_original[ii] = output_dic['meta']['metrics']['original']['crispness_corr']
        if 'rigid' in output_dic['meta']['metrics'].keys():
            crispness_mean[ii] = output_dic['meta']['metrics']['rigid']['crispness']
            crispness_corr[ii] = output_dic['meta']['metrics']['rigid']['crispness_corr']
        else:
            crispness_mean[ii] = output_dic['meta']['metrics']['pw_rigid']['crispness']
            crispness_corr[ii] = output_dic['meta']['metrics']['pw_rigid']['crispness_corr']

    return crispness_mean_original,crispness_corr_original, crispness_mean, crispness_corr

def select_corr_pnr_threshold(mouse_row,parameters_source_extraction):
    '''
     Plots the summary images correlation and pnr. Also the pointwise product between them (used in Caiman paper Zhou
     et al 2018)
     :param mouse_row:
     :param parameters_source_extraction: parameters that will be used for source
     extraction. the relevant parameter here are min_corr and min_pnr because the source extraction algorithm is
     initialized (initial cell templates) in all values that surpasses that threshold
     :return:  max_combined, max_pnr, max_corr: threshold for corr*pnr, and corresponding values of corr and pnr

     '''

    input_mmap_file_path = eval(mouse_row.loc['motion_correction_output'])['main']

    # Load memory mappable input file
    if os.path.isfile(input_mmap_file_path):
        Yr, dims, T = cm.load_memmap(input_mmap_file_path)
        #        logging.debug(f'{index} Loaded movie. dims = {dims}, T = {T}.')
        images = Yr.T.reshape((T,) + dims, order='F')
    else:
        logging.warning(f'{mouse_row.name} .mmap file does not exist. Cancelling')

    # Determine output paths
    step_index = db.get_step_index('motion_correction')
    data_dir = 'data/interim/source_extraction/trial_wise/'

    # Check if the summary images are already there
    gSig = parameters_source_extraction['gSig'][0]
    corr_npy_file_path, pnr_npy_file_path = fm.get_corr_pnr_path(mouse_row.name, gSig_abs=(gSig, gSig))

    if corr_npy_file_path != None and os.path.isfile(corr_npy_file_path):
        # Already computed summary images
        logging.info(f'{mouse_row.name} Already computed summary images')
        cn_filter = np.load(corr_npy_file_path)
        pnr = np.load(pnr_npy_file_path)
    else:
        # Compute summary images
        t0 = datetime.datetime.today()
        logging.info(f'{mouse_row.name} Computing summary images')
        cn_filter, pnr = cm.summary_images.correlation_pnr(images[::1], gSig=parameters_source_extraction['gSig'][0],
                                                           swap_dim=False)
        # Saving summary images as npy files
        corr_npy_file_path = data_dir + f'meta/corr/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}.npy'
        pnr_npy_file_path = data_dir + f'meta/pnr/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}.npy'
        with open(corr_npy_file_path, 'wb') as f:
            np.save(f, cn_filter)
        with open(pnr_npy_file_path, 'wb') as f:
            np.save(f, pnr)

    combination = cn_filter * pnr # this is as defined in Zhou et al 2018 (definition of R, P and L, eq 14)
    max_combined = np.argmax(combination)
    row = int(np.floor(max_combined / cn_filter.shape[1]))
    column = int(max_combined - row * cn_filter.shape[1])
    max_corr = cn_filter[row, column]
    max_pnr = pnr[row, column]

    return max_combined, max_corr, max_pnr


def create_corr_pnr_histogram(mouse_row,parameters_source_extraction):
    '''
     Returns histogram of summary images correlation and pnr
     :param mouse_row:
     :param parameters_source_extraction: parameters that will be used for source extraction.
     :return:  histogram vector

     '''

    input_mmap_file_path = eval(mouse_row.loc['motion_correction_output'])['main']

    # Load memory mappable input file
    if os.path.isfile(input_mmap_file_path):
        Yr, dims, T = cm.load_memmap(input_mmap_file_path)
        #        logging.debug(f'{index} Loaded movie. dims = {dims}, T = {T}.')
        images = Yr.T.reshape((T,) + dims, order='F')
    else:
        logging.warning(f'{mouse_row.name} .mmap file does not exist. Cancelling')

    # Determine output paths
    step_index = db.get_step_index('motion_correction')
    data_dir = 'data/interim/source_extraction/trial_wise/'

    # Check if the summary images are already there
    gSig = parameters_source_extraction['gSig'][0]
    corr_npy_file_path, pnr_npy_file_path = fm.get_corr_pnr_path(mouse_row.name, gSig_abs=(gSig, gSig))

    if corr_npy_file_path != None and os.path.isfile(corr_npy_file_path):
        # Already computed summary images
        logging.info(f'{mouse_row.name} Already computed summary images')
        cn_filter = np.load(corr_npy_file_path)
        pnr = np.load(pnr_npy_file_path)
    else:
        # Compute summary images
        t0 = datetime.datetime.today()
        logging.info(f'{mouse_row.name} Computing summary images')
        cn_filter, pnr = cm.summary_images.correlation_pnr(images[::1], gSig=parameters_source_extraction['gSig'][0],
                                                           swap_dim=False)
        # Saving summary images as npy files
        corr_npy_file_path = data_dir + f'meta/corr/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}.npy'
        pnr_npy_file_path = data_dir + f'meta/pnr/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}.npy'
        with open(corr_npy_file_path, 'wb') as f:
            np.save(f, cn_filter)
        with open(pnr_npy_file_path, 'wb') as f:
            np.save(f, pnr)


    corr_pos, corr_histogram = np.histogram(cn_filter,100)
    pnr_pos, pnr_histogram = np.histogram(pnr,100)

    return corr_pos, corr_histogram, pnr_pos, pnr_histogram