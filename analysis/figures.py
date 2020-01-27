#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""


@author: Melisa Maidana,Morgane


Functions in this python file are related to plotting different stages of the calcium imaging analysis pipeline.

Most of the save the result in the corresponding folder of the particular step.

"""


import pylab as pl
import caiman as cm
import matplotlib.pyplot as plt
import math
import numpy as np
from caiman.motion_correction import high_pass_filter_space
from caiman.source_extraction.cnmf.cnmf import load_CNMF

import analysis.metrics as metrics
import logging
import os
import datetime
import analysis.analysis_files_manipulation as fm
from caiman.source_extraction.cnmf.initialization import downscale
from Database.database_connection import database

mycursor = database.cursor()


def plot_movie_frame(decoded_file):

    """

    This function creates an image for visual inspection of cropping points.

    """
    m = cm.load(decoded_file)
    pl.imshow(m[0,:,:],cmap='gray')
    return

def plot_movie_frame_cropped(cropped_file):

    """

    This function creates an image for visual inspections of cropped frame

    """

    m = cm.load(cropped_file)
    pl.imshow(m[0,:,:],cmap='gray')
    return


def get_fig_gSig_filt_vals(cropped_file, gSig_filt_vals):

    """

    Plot original cropped frame and several versions of spatial filtering for comparison
    :param cropped_file
    :param gSig_filt_vals: array containing size of spatial filters that will be applied
    :return: figure

    """

    m = cm.load(cropped_file)
    temp = cm.motion_correction.bin_median(m)
    N = len(gSig_filt_vals)
    fig, axes = plt.subplots(int(math.ceil((N + 1) / 2)), 2)
    axes[0, 0].imshow(temp, cmap='gray')
    axes[0, 0].set_title('unfiltered')
    axes[0, 0].axis('off')
    for i in range(0, N):
        gSig_filt = gSig_filt_vals[i]
        m_filt = [high_pass_filter_space(m_, (gSig_filt, gSig_filt)) for m_ in m]
        temp_filt = cm.motion_correction.bin_median(m_filt)
        axes.flatten()[i + 1].imshow(temp_filt, cmap='gray')
        axes.flatten()[i + 1].set_title(f'gSig_filt = {gSig_filt}')
        axes.flatten()[i + 1].axis('off')
    if N + 1 != axes.size:
        for i in range(N + 1, axes.size):
            axes.flatten()[i].axis('off')

    # Get output file paths
    sql="SELECT mouse,session,trial,is_rest,cropping_v,decoding_v,motion_correction_v FROM Analysis WHERE cropping_main=%s "
    val=[cropped_file,]
    mycursor.execute(sql,val)
    myresult = mycursor.fetchall()
    data=[]
    for x in myresult:
        data+=x

    file_name = f"mouse_{data[0]}_session_{data[1]}_trial_{data[2]}.{data[3]}.v{data[5]}.{data[4]}.{data[6]}"
    data_dir = 'data/interim/motion_correction/'
    output_meta_gSig_filt = data_dir + f'meta/figures/frame_gSig_filt/{file_name}.png'

    fig.savefig(output_meta_gSig_filt)

    return fig

def plot_crispness_for_parameters(selected_rows = None):
    '''
    This function plots crispness for all the selected rows motion correction states. The idea is to compare crispness results
    :param selected_rows: analysis states for which crispness is required to be ploted
    :return: figure that is also saved
    '''
    crispness_mean_original,crispness_corr_original, crispness_mean, crispness_corr = metrics.compare_crispness(selected_rows)
    total_states_number = len(selected_rows)

    fig, axes = plt.subplots(1,2)
    axes[0].set_title('Summary image = Mean')
    axes[0].plot(np.arange(1,total_states_number,1),crispness_mean_original)
    axes[0].plot(np.arange(1,total_states_number,1),crispness_mean)
    axes[0].legend(('Original', 'Motion_corrected'))
    axes[0].set_ylabel('Crispness')
    #axes[0].set_xlabel('#')

    axes[1].set_title('Summary image = Corr')
    axes[1].plot(np.arange(1,total_states_number,1),crispness_corr_original)
    axes[1].plot(np.arange(1,total_states_number,1),crispness_corr)
    axes[1].legend(('Original', 'Motion_corrected'))
    axes[1].set_ylabel('Crispness')
    #axes[0].set_xlabel('#')

    # Get output file paths
    index = selected_rows.iloc[0].name
    data_dir = 'data/interim/motion_correction/'
    step_index = db.get_step_index('motion_correction')
    file_name = db.create_file_name(step_index, index)
    output_meta_crispness = data_dir + f'meta/figures/crispness/{file_name}.png'

    fig.savefig(output_meta_crispness)
    return fig

def plot_corr_pnr(mouse_row, parameters_source_extraction):
    '''
    Plots the summary images correlation and pnr. Also the pointwise product between them (used in Caiman paper Zhou
    et al 2018)
    :param mouse_row:
    :param parameters_source_extraction: parameters that will be used for source
    extraction. the relevant parameter here are min_corr and min_pnr because the source extraction algorithm is
    initialized (initial cell templates) in all values that surpasses that threshold
    :return:  figure
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

    fig = plt.figure(figsize=(15, 15))
    min_corr = round(parameters_source_extraction['min_corr'], 2)
    min_pnr = round(parameters_source_extraction['min_pnr'], 1)
    max_corr = round(cn_filter.max(), 2)
    max_pnr= 20

    # continuous
    cmap = 'viridis'
    fig, axes = plt.subplots(1, 3, sharex=True)

    corr_fig = axes[0].imshow(np.clip(cn_filter,min_corr,max_corr), cmap=cmap)
    axes[0].set_title('Correlation')
    fig.colorbar(corr_fig, ax=axes[0])
    pnr_fig = axes[1].imshow(np.clip(pnr,min_pnr,max_pnr), cmap=cmap)
    axes[1].set_title('PNR')
    fig.colorbar(pnr_fig, ax=axes[1])
    combined = cn_filter*pnr
    max_combined = 10
    min_combined = np.min(combined)
    corr_pnr_fig = axes[2].imshow(np.clip(cn_filter*pnr,min_combined,max_combined), cmap=cmap)
    axes[2].set_title('Corr * PNR')
    fig.colorbar(corr_pnr_fig, ax=axes[2])

    fig_dir = 'data/interim/source_extraction/trial_wise/meta/'
    fig_name= fig_dir + f'figures/corr_pnr/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}.png'
    fig.savefig(fig_name)

    return fig

def plot_corr_pnr_binary(mouse_row, corr_limits, pnr_limits, parameters_source_extraction, session_wise = False):
    '''
    Plot 2 matrix of binary selected and not selected seeds for different corr_min and pnr_min
    :param mouse_row: analysis states data
    :param corr_limits: array of multiple values of corr_min to test
    :param pnr_limits: arrey of multiple values of pnr_min to test
    :param parameters_source_extraction: dictionary with parameters
    :return: figure pointer
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

    fig1 = plt.figure(figsize=(50, 50))

    combined_image = cn_filter * pnr
    fig1, axes1 = plt.subplots(len(corr_limits), len(pnr_limits), sharex=True)
    fig2, axes2 = plt.subplots(len(corr_limits), len(pnr_limits), sharex=True)
    fig3, axes3 = plt.subplots(len(corr_limits), len(pnr_limits), sharex=True)

    ii=0
    for min_corr in corr_limits:
        min_corr = round(min_corr,2)
        jj=0
        for min_pnr in pnr_limits:
            min_pnr = round(min_pnr,2)
            # binary
            limit = min_corr * min_pnr
            axes1[ii, jj].imshow(combined_image> limit, cmap='binary')
            axes1[ii, jj].set_title(f'{min_corr}')
            axes1[ii, jj].set_ylabel(f'{min_pnr}')
            axes2[ii, jj].imshow(cn_filter > min_corr, cmap='binary')
            axes2[ii, jj].set_title(f'{min_corr}')
            axes2[ii, jj].set_ylabel(f'{min_pnr}')
            axes3[ii, jj].imshow(pnr> min_pnr, cmap='binary')
            axes3[ii, jj].set_title(f'{min_corr}')
            axes3[ii, jj].set_ylabel(f'{min_pnr}')
            jj=jj+1
        ii=ii+1

    fig_dir = 'data/interim/source_extraction/trial_wise/meta/'
    if session_wise:
        fig_dir = 'data/interim/source_extraction/session_wise/meta/'
    fig_name= fig_dir + f'figures/min_corr_pnr/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}_comb.png'
    fig1.savefig(fig_name)


    fig_name= fig_dir + f'figures/min_corr_pnr/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}_corr.png'
    fig2.savefig(fig_name)

    fig_name= fig_dir + f'figures/min_corr_pnr/{db.create_file_name(3, mouse_row.name)}_gSig_{gSig}_pnr.png'
    fig3.savefig(fig_name)

    return fig1,fig2,fig3



def plot_histogram(position, value , title = 'title', xlabel = 'x_label', ylabel = 'y_label'):
    '''
    This function plots a histogram for...
    :param position: x marks
    :param value: y marks
    :param title:
    :param xlabel:
    :param ylabel:
    :return:
    '''

    fig, axes = plt.subplots(1, 1, sharex=True)

    normalization = sum(value)
    axes.plot(position, value / normalization)
    axes.set_title(title)
    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)
    axes.set_ylim(0, np.max(value/normalization) + 0.01 *np.max(value/normalization))

    return fig


def plot_multiple_contours(row, version = None , corr_array = None, pnr_array = None,session_wise = False):
    '''
    Plots different versions of contour images that change the initialization parameters for source extraction.
    The idea is to see the impact of different seed selection in the final source extraction result.
    :param row: one analysis state row
    :param version: array containing the version numbers of source extraction that will be plotted
    :param corr_array: array of the same length of version and pnr_array containing the min_corr values for those versions
    :param pnr_array: array of the same length of version and corr_array containing the min_pnr values for those versions
    :return: figure
    '''

    states_df = db.open_analysis_states_database()
    index = row.name

    figure, axes = plt.subplots(len(corr_array), len(pnr_array), figsize=(15, 15))

    for ii in range(corr_array.shape[0]):
        for jj in range(pnr_array.shape[0]):
            new_row = db.select(states_df,'component_evaluation',mouse =index[0],session = index[1],
                                     trial = index[2], is_rest = index[3], cropping_v= index[5], motion_correction_v=index[6],
                                     source_extraction_v = version[ii*len(pnr_array)+jj])
            new_row = new_row.iloc[0]

            output = eval(new_row.loc['source_extraction_output'])
            cnm_file_path = output['main']
            cnm = load_CNMF(db.get_file(cnm_file_path))
            corr_path = output['meta']['corr']['main']
            cn_filter = np.load(db.get_file(corr_path))
            axes[ii, jj].imshow(cn_filter)
            coordinates = cm.utils.visualization.get_contours(cnm.estimates.A, np.shape(cn_filter), 0.2, 'max')
            for c in coordinates:
                v = c['coordinates']
                c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                             np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
                axes[ii, jj].plot(*v.T, c='w')
            axes[ii, jj].set_title('min_corr = ' + f'{round(corr_array[ii],2)}')
            axes[ii, jj].set_ylabel('min_pnr = ' + f'{round(pnr_array[jj],2)}')


    fig_dir = 'data/interim/source_extraction/trial_wise/meta/figures/contours/'
    if session_wise:
        fig_dir = 'data/interim/source_extraction/session_wise/meta/figures/contours/'
    fig_name = fig_dir + db.create_file_name(3, new_row.name)+'_corr_min' + f'{round(corr_array[0],1)}'+ '_pnr_min'+f'{round(pnr_array[0],1)}' + '_.png'
    figure.savefig(fig_name)

    return figure


def plot_session_contours(selected_rows, version = None , corr_array = None, pnr_array = None):
    '''
    Plots different versions of contour images that change the initialization parameters for source extraction.
    The idea is to see the impact of different seed selection in the final source extraction result.
    :param selected_rows: rows corresponding to different trials
    :param version: array containing the version numbers of source extraction that will be plotted
    :param corr_array: array of the same length of version and pnr_array containing the min_corr values for those versions
    :param pnr_array: array of the same length of version and corr_array containing the min_pnr values for those versions
    :return: (saves multiple figures)
    '''

    states_df = db.open_analysis_states_database()

    for ii in range(corr_array.shape[0]):
        for jj in range(pnr_array.shape[0]):

            figure, axes = plt.subplots(1, len(selected_rows), figsize=(50, 10))

            for i in range(len(selected_rows)):
                row = selected_rows.iloc[i]
                index = row.name
                new_row = db.select(states_df,'component_evaluation',mouse =index[0],session = index[1],
                                     trial = index[2], is_rest = index[3], cropping_v= index[5], motion_correction_v=index[6],
                                     alignment_v= index[7], source_extraction_v = version[ii*len(pnr_array)+jj])
                new_row = new_row.iloc[0]

                output = eval(new_row.loc['source_extraction_output'])
                cnm_file_path = output['main']
                cnm = load_CNMF(db.get_file(cnm_file_path))
                corr_path = output['meta']['corr']['main']
                cn_filter = np.load(db.get_file(corr_path))
                #axes[i].imshow(np.clip(cn_filter, min_corr, max_corr), cmap='viridis')
                axes[i].imshow(cn_filter)
                coordinates = cm.utils.visualization.get_contours(cnm.estimates.A, np.shape(cn_filter), 0.2, 'max')
                for c in coordinates:
                    v = c['coordinates']
                    c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                                 np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
                    axes[i].plot(*v.T, c='w')
                axes[i].set_title('Trial = ' + f'{i+1}',fontsize=30)
                axes[i].set_xlabel('#cells = ' + f'{cnm.estimates.A.shape[1]}',fontsize=30)

            figure.suptitle('min_corr = ' + f'{round(corr_array[ii],2)}' + 'min_pnr = ' + f'{round(pnr_array[jj],2)}', fontsize=50)

            fig_dir = 'data/interim/source_extraction/session_wise/meta/figures/contours/'
            fig_name = fig_dir + db.create_file_name(3, new_row.name)+'_version_' + f'{version[ii*len(pnr_array)+jj]}'+'.png'
            figure.savefig(fig_name)

    return



def plot_multiple_contours_session_wise(selected_rows, version = None , corr_array = None, pnr_array = None):
    '''
    Plots different versions of contour images that change the initialization parameters for source extraction.
    The idea is to see the impact of different seed selection in the final source extraction result.
    :param selected_rows: all analysis state selected
    :param version: array containing the version numbers of source extraction that will be plotted
    :param corr_array: array of the same length of version and pnr_array containing the min_corr values for those versions
    :param pnr_array: array of the same length of version and corr_array containing the min_pnr values for those versions
    :return: figure
    '''

    states_df = db.open_analysis_states_database()

    figure, axes = plt.subplots(len(corr_array), len(pnr_array), figsize=(15, 15))

    color = ['w','b','r','m','c']
    for row in range(len(selected_rows)):
        mouse_row = selected_rows.iloc[row]
        index = mouse_row.name
        output = eval(mouse_row.loc['source_extraction_output'])
        corr_path = output['meta']['corr']['main']
        cn_filter = np.load(db.get_file(corr_path))
        for ii in range(corr_array.shape[0]):
            for jj in range(pnr_array.shape[0]):
                axes[ii, jj].imshow(cn_filter)
                new_row = db.select(states_df, 'component_evaluation', mouse=index[0], session=index[1],
                                    trial=index[2], is_rest=index[3], cropping_v=index[5], motion_correction_v=index[6],
                                    source_extraction_v=version[ii * len(pnr_array) + jj])
                new_row = new_row.iloc[0]
                output = eval(new_row.loc['source_extraction_output'])
                cnm_file_path = output['main']
                cnm = load_CNMF(db.get_file(cnm_file_path))
                coordinates = cm.utils.visualization.get_contours(cnm.estimates.A, np.shape(cn_filter), 0.2, 'max')
                for c in coordinates:
                    v = c['coordinates']
                    c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                                 np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
                    axes[ii, jj].plot(*v.T, c = color[row])
                axes[ii, jj].set_title('min_corr = ' + f'{round(corr_array[ii],2)}')
                axes[ii, jj].set_ylabel('min_pnr = ' + f'{round(pnr_array[jj],2)}')


    fig_dir = 'data/interim/source_extraction/session_wise/meta/figures/contours/'
    fig_name = fig_dir + db.create_file_name(3, new_row.name)+'_corr_min' + f'{round(corr_array[0],1)}'+ '_pnr_min'+f'{round(pnr_array[0],1)}' + '_all.png'
    figure.savefig(fig_name)

    return figure


def plot_multiple_contours_session_wise_evaluated(selected_rows):

    ## IN DEVELOPMENT!!!!!!!
    '''
    Plots different versions of contour images that change the initialization parameters for source extraction.
    The idea is to see the impact of different seed selection in the final source extraction result.
    :param selected_rows: all analysis state selected
    :return: figure
    '''

    figure, axes = plt.subplots(3, 5, figsize=(50, 30))

    for row in range(len(selected_rows)):
        mouse_row = selected_rows.iloc[row]
        index = mouse_row.name
        output = eval(mouse_row.loc['source_extraction_output'])
        corr_path = output['meta']['corr']['main']
        cn_filter = np.load(db.get_file(corr_path))
        axes[0,row].imshow(cn_filter)
        axes[1,row].imshow(cn_filter)
        axes[2,row].imshow(cn_filter)
        output = eval(mouse_row.loc['source_extraction_output'])
        cnm_file_path = output['main']
        cnm = load_CNMF(db.get_file(cnm_file_path))
        coordinates = cm.utils.visualization.get_contours(cnm.estimates.A, np.shape(cn_filter), 0.2, 'max')
        for c in coordinates:
            v = c['coordinates']
            c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                         np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
            axes[0,row].plot(*v.T, c = 'w', linewidth=3)
        axes[0,row].set_title('Trial = ' + f'{row}')
        axes[0,row].set_ylabel('')

        output = eval(mouse_row.loc['component_evaluation_output'])
        cnm_file_path = output['main']
        cnm = load_CNMF(db.get_file(cnm_file_path))
        idx = cnm.estimates.idx_components
        coordinates = cm.utils.visualization.get_contours(cnm.estimates.A[:, idx], np.shape(cn_filter), 0.2, 'max')
        for c in coordinates:
            v = c['coordinates']
            c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                         np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
            axes[1,row].plot(*v.T, c='b', linewidth=3)

        idx_b = cnm.estimates.idx_components_bad
        coordinates_b = cm.utils.visualization.get_contours(cnm.estimates.A[:,idx_b], np.shape(cn_filter), 0.2, 'max')

        for c in coordinates_b:
            v = c['coordinates']
            c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                         np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
            axes[2,row].plot(*v.T, c='r', linewidth=3)


    source_extraction_parameters = eval(mouse_row['source_extraction_parameters'])
    corr_lim = source_extraction_parameters['min_corr']
    pnr_lim = source_extraction_parameters['min_pnr']
    component_evaluation_parameters = eval(mouse_row['component_evaluation_parameters'])
    pcc = component_evaluation_parameters['rval_thr']
    SNR = component_evaluation_parameters['min_SNR']
    figure.suptitle('Corr = ' + f'{corr_lim}' + 'PNR = ' + f'{pnr_lim}' + 'PCC = ' + f'{pcc}' + 'SNR = ' + f'{SNR}',
                    fontsize=50)
    fig_dir = 'data/interim/component_evaluation/session_wise/meta/figures/contours/'
    fig_name = fig_dir + db.create_file_name(3, index)+'_Corr = ' + f'{corr_lim}' + '_PNR = ' + f'{pnr_lim}' + '_PCC = ' + f'{pcc}' + '_SNR = ' + f'{SNR}' +'_.png'
    figure.savefig(fig_name)

    return figure


def plot_traces_multiple(row, version = None , corr_array = None, pnr_array = None, session_wise = False):
    '''
    Plots different versions of contour images that change the inicialization parameters for source extraccion.
    The idea is to see the impact of different seed selection in the final source extraction result.
    :param row: one analysis state row
    :param version: array containing the version numbers of source extraction that will be ploted
    :param corr_array: array of the same length of version and pnr_array containing the min_corr values for those versions
    :param pnr_array: array of the same length of version and corr_array containing the min_pnr values for those versions
    :param: session_wise bool that indicates where the figure is save
    :return: None
    '''

    states_df = db.open_analysis_states_database()
    index = row.name

    for ii in range(corr_array.shape[0]):
        for jj in range(pnr_array.shape[0]):
            fig, ax = plt.subplots(1)
            new_row = db.select(states_df, 'component_evaluation', mouse=index[0], session=index[1],
                                trial=index[2], is_rest=index[3], cropping_v=index[5], motion_correction_v=index[6],
                                alignment_v= index[7], source_extraction_v=version[ii * len(pnr_array) + jj])
            new_row = new_row.iloc[0]

            output = eval(new_row.loc['source_extraction_output'])
            cnm_file_path = output['main']
            cnm = load_CNMF(db.get_file(cnm_file_path))
            C = cnm.estimates.C
            idx_components = cnm.estimates.idx_components
            C[0] += C[0].min()
            for i in range(1, len(C)):
                C[i] += C[i].min() + C[:i].max()
                ax.plot(C[i])
            ax.set_xlabel('t [frames]')
            ax.set_yticks([])
            ax.set_ylabel('activity')
            fig.set_size_inches([10., .3 * len(C)])


            fig_dir = 'data/interim/source_extraction/trial_wise/meta/figures/traces/'
            if session_wise:
                fig_dir = 'data/interim/source_extraction/session_wise/meta/figures/traces/'
            fig_name = fig_dir + db.create_file_name(3,new_row.name) + '_corr_min' + f'{round(corr_array[ii], 1)}' + '_pnr_min' + f'{round(pnr_array[jj], 1)}' + '_.png'
            fig.savefig(fig_name)

    return


def plot_contours_evaluated(row = None):
    '''
    Plot contours for all cells, selected cells and non selected cells, and saves it in
    figure_path = '/data/interim/component_evaluation/trial_wise/meta/figures/contours/'
    :param row: one analysis state row
    '''
    index = row.name

    corr_min = round(eval(row['source_extraction_parameters'])['min_corr'],1)
    pnr_min = round(eval(row['source_extraction_parameters'])['min_pnr'],1)
    r_min = eval(row['component_evaluation_parameters'])['rval_thr']
    snf_min = eval(row['component_evaluation_parameters'])['min_SNR']

    output_source_extraction = eval(row.loc['source_extraction_output'])
    corr_path = output_source_extraction['meta']['corr']['main']
    cn_filter = np.load(db.get_file(corr_path))

    output_component_evaluation =  eval(row.loc['component_evaluation_output'])
    cnm_file_path = output_component_evaluation['main']
    cnm = load_CNMF(db.get_file(cnm_file_path))
    figure, axes = plt.subplots(1, 3)
    axes[0].imshow(cn_filter)
    axes[1].imshow(cn_filter)
    axes[2].imshow(cn_filter)

    coordinates = cm.utils.visualization.get_contours(cnm.estimates.A, np.shape(cn_filter), 0.2, 'max')
    for c in coordinates:
        v = c['coordinates']
        c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                     np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
        axes[0].plot(*v.T, c='w')
    axes[0].set_title('All components')
    axes[0].set_ylabel('Corr=' + f'{corr_min}' + ', PNR = ' + f'{pnr_min}' + ', PCC = ' + f'{r_min}' + ', SNR =' + f'{snf_min}')

    idx = cnm.estimates.idx_components
    coordinates = cm.utils.visualization.get_contours(cnm.estimates.A[:,idx], np.shape(cn_filter), 0.2, 'max')

    for c in coordinates:
        v = c['coordinates']
        c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                     np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
        axes[1].plot(*v.T, c='b')
    axes[1].set_title('Accepted components')

    idx_b = cnm.estimates.idx_components_bad
    coordinates_b = cm.utils.visualization.get_contours(cnm.estimates.A[:,idx_b], np.shape(cn_filter), 0.2, 'max')

    for c in coordinates_b:
        v = c['coordinates']
        c['bbox'] = [np.floor(np.nanmin(v[:, 1])), np.ceil(np.nanmax(v[:, 1])),
                     np.floor(np.nanmin(v[:, 0])), np.ceil(np.nanmax(v[:, 0]))]
        axes[2].plot(*v.T, c='r')
    axes[2].set_title('Rejected components')

    figure_path = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/component_evaluation/trial_wise/meta/figures/contours/'
    figure_name = figure_path + db.create_file_name(5,index) + '.png'
    figure.savefig(figure_name)
    return figure

def plot_traces_multiple_evaluated(row):
    '''
    Plots different versions of contour images that change the inicialization parameters for source extraccion.
    The idea is to see the impact of different seed selection in the final source extraction result.
    :param row: one analysis state row
    :return: figure
    '''

    corr_min = round(eval(row['source_extraction_parameters'])['min_corr'],1)
    pnr_min = round(eval(row['source_extraction_parameters'])['min_pnr'],1)
    r_min = eval(row['component_evaluation_parameters'])['rval_thr']
    snf_min = eval(row['component_evaluation_parameters'])['min_SNR']

    output_source_extraction = eval(row.loc['source_extraction_output'])
    corr_path = output_source_extraction['meta']['corr']['main']
    cn_filter = np.load(db.get_file(corr_path))
    cnm_file_path = output_source_extraction['main']
    cnm = load_CNMF(db.get_file(cnm_file_path))
    C = cnm.estimates.C

    output_component_evaluation =  eval(row.loc['component_evaluation_output'])
    cnm_file_path = output_component_evaluation['main']
    cnm_eval = load_CNMF(db.get_file(cnm_file_path))
    idx = cnm_eval.estimates.idx_components
    idx_b = cnm_eval.estimates.idx_components_bad

    fig, ax = plt.subplots(1)
    C[0] += C[0].min()
    for i in range(1, len(C)):
        C[i] += C[i].min() + C[:i].max()
        if i in idx_b:
            color = 'red'
        else:
            color = 'blue'
        ax.plot(C[i],color = color)
    ax.set_xlabel('t [frames]')
    ax.set_yticks([])
    ax.set_ylabel('activity')
    ax.set_title('Corr=' + f'{corr_min}' + ', PNR = ' + f'{pnr_min}' + ', PCC = ' + f'{r_min}' + ', SNR =' + f'{snf_min}')

    fig.set_size_inches([10., .3 * len(C)])

    fig_dir = 'data/interim/component_evaluation/trial_wise/meta/figures/traces/'
    fig_name = fig_dir + db.create_file_name(5,row.name) + '.png'
    fig.savefig(fig_name)

    return

def play_movie(estimates, imgs, q_max=99.75, q_min=2, gain_res=1,
                   magnification=1, include_bck=True,
                   frame_range=slice(None, None, None),
                   bpx=0, thr=0., save_movie=False,
                   movie_name='results_movie.avi'):

    dims = imgs.shape[1:]
    if 'movie' not in str(type(imgs)):
        imgs = cm.movie(imgs)
    Y_rec = estimates.A.dot(estimates.C[:, frame_range])
    Y_rec = Y_rec.reshape(dims + (-1,), order='F')
    Y_rec = Y_rec.transpose([2, 0, 1])

    if estimates.W is not None:
        ssub_B = int(round(np.sqrt(np.prod(dims) / estimates.W.shape[0])))
        B = imgs[frame_range].reshape((-1, np.prod(dims)), order='F').T - \
            estimates.A.dot(estimates.C[:, frame_range])
        if ssub_B == 1:
            B = estimates.b0[:, None] + estimates.W.dot(B - estimates.b0[:, None])
        else:
            B = estimates.b0[:, None] + (np.repeat(np.repeat(estimates.W.dot(
                downscale(B.reshape(dims + (B.shape[-1],), order='F'),
                          (ssub_B, ssub_B, 1)).reshape((-1, B.shape[-1]), order='F') -
                downscale(estimates.b0.reshape(dims, order='F'),
                          (ssub_B, ssub_B)).reshape((-1, 1), order='F'))
                    .reshape(((dims[0] - 1) // ssub_B + 1, (dims[1] - 1) // ssub_B + 1, -1), order='F'),
                    ssub_B, 0), ssub_B, 1)[:dims[0], :dims[1]].reshape((-1, B.shape[-1]), order='F'))
        B = B.reshape(dims + (-1,), order='F').transpose([2, 0, 1])
    elif estimates.b is not None and estimates.f is not None:
        B = estimates.b.dot(estimates.f[:, frame_range])
        if 'matrix' in str(type(B)):
            B = B.toarray()
        B = B.reshape(dims + (-1,), order='F').transpose([2, 0, 1])
    else:
        B = np.zeros_like(Y_rec)
    if bpx > 0:
        B = B[:, bpx:-bpx, bpx:-bpx]
        Y_rec = Y_rec[:, bpx:-bpx, bpx:-bpx]
        imgs = imgs[:, bpx:-bpx, bpx:-bpx]

    Y_res = imgs[frame_range] - Y_rec - B

    mov = cm.concatenate((imgs[frame_range] - (not include_bck) * B, Y_rec,
                            Y_rec + include_bck * B, Y_res * gain_res), axis=2)

    if thr > 0:
        if save_movie:
            import cv2
            #fourcc = cv2.VideoWriter_fourcc('8', 'B', 'P', 'S')
            #fourcc = cv2.VideoWriter_fourcc(*'XVID')
            fourcc = cv2.VideoWriter_fourcc(*'MP4V')
            out = cv2.VideoWriter(movie_name, fourcc, 30.0,
                                  tuple([int(magnification*s) for s in mov.shape[1:][::-1]]))
        contours = []
        for a in estimates.A.T.toarray():
            a = a.reshape(dims, order='F')
            if bpx > 0:
                a = a[bpx:-bpx, bpx:-bpx]
            if magnification != 1:
                a = cv2.resize(a, None, fx=magnification, fy=magnification,
                               interpolation=cv2.INTER_LINEAR)
            ret, thresh = cv2.threshold(a, thr * np.max(a), 1., 0)
            contour, hierarchy = cv2.findContours(
                thresh.astype('uint8'), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours.append(contour)
            contours.append(list([c + np.array([[a.shape[1], 0]]) for c in contour]))
            contours.append(list([c + np.array([[2 * a.shape[1], 0]]) for c in contour]))

        maxmov = np.nanpercentile(mov[0:10], q_max) if q_max < 100 else np.nanmax(mov)
        minmov = np.nanpercentile(mov[0:10], q_min) if q_min > 0 else np.nanmin(mov)
        for frame in mov:
            if magnification != 1:
                frame = cv2.resize(frame, None, fx=magnification, fy=magnification,
                                   interpolation=cv2.INTER_LINEAR)
            frame = np.clip((frame - minmov) * 255. / (maxmov - minmov), 0, 255)
            frame = np.repeat(frame[..., None], 3, 2)
            for contour in contours:
                cv2.drawContours(frame, contour, -1, (0, 255, 255), 1)
            cv2.imshow('frame', frame.astype('uint8'))
            if save_movie:
                out.write(frame.astype('uint8'))
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
        if save_movie:
            out.release()
        cv2.destroyAllWindows()
        cv2.destroyAllWindows()
    else:
        mov.play(q_min=q_min, q_max=q_max, magnification=magnification,
                     save_movie=save_movie, movie_name=movie_name)

    return
