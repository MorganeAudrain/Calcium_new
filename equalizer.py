# -*- coding: utf-8 -*-
"""
@author: Melisa
"""

import logging
import matplotlib.pyplot as plt
import caiman as cm
import caiman.motion_correction
from caiman.motion_correction import MotionCorrect, high_pass_filter_space
from caiman.source_extraction.cnmf import params as params
from caiman.mmapping import load_memmap

import datetime
import os
import numpy as np
import pickle
import math
import scipy
import scipy.stats

import src.data_base_manipulation as db
import src.paths as paths
from random import randint
from skimage import io

h_step = 10
parameters_equalizer = {'make_template_from_trial': '6_R', 'equalizer': 'histogram_matching', 'histogram_step': h_step}
parameters = parameters_equalizer

def run_equalizer(states_df, parameters):
    '''

    This function is meant to help with differences in different trials and session, to equalize general brightness
    or reduce photobleaching. It corrects the video and saves them in the corrected version.

    params df: pd.DataFrame -> A dataframe containing the analysis states you want to have aligned.
    params parameters: dict -> contains parameters concerning equalization

    returns df: pd.DataFrame -> A dataframe containing the aligned analysis states.
    '''

    # Sort the dataframe correctly
    df = states_df.sort_values(by=paths.multi_index_structure)
    # Determine the output path
    output_mmap_file_path = f'data/interim/equalizer/main/'
    mouse, session, init_trial, *r = df.iloc[0].name

    histogram_name = f'mouse_{mouse}_session_{session}_init_trial_{init_trial}'
    output_steps_file_path = f'data/interim/equalizer/meta/figures/histograms/'+histogram_name

    try:
        df.reset_index()[['trial', 'is_rest']].set_index(['trial', 'is_rest'], verify_integrity=True)
    except ValueError:
        logging.error('You passed multiple of the same trial in the dataframe df')
        return df

    output = {
        'meta': {
            'analysis': {
                'analyst': os.environ['ANALYST'],
                'date': datetime.datetime.today().strftime("%m-%d-%Y"),
                'time': datetime.datetime.today().strftime("%H:%M:%S")
            },
            'duration': {}
        }
    }

    # Get necessary parameters
    decoding_output_list = []
    input_tif_file_list = []
    trial_index_list = []
    for idx, row in df.iterrows():
        decoding_output = eval(row.loc['decoding_output'])
        decoding_output_list.append(decoding_output)
        input_tif_file_list.append(decoding_output['main'])
        trial_index_list.append(db.get_trial_name(idx[2], idx[3]))

    colors = []
    for i in range(len(df)):
        colors.append('#%06X' % randint(0, 0xFFFFFF))

    m_list = []
    m_reshape_list=[]
    legend = []
    min_list = []
    max_list = []
    h_step = parameters['histogram_step']
    fig, ax = plt.subplots(1,2)

    for i in range(len(input_tif_file_list)):
        im = io.imread(input_tif_file_list[i])
        #m_list.append(im)
        reshape_m = np.reshape(im, (im.shape[0] * im.shape[1] * im.shape[2]))
        m_reshape_list.append(reshape_m)
        legend.append('trial = ' + f'{df.iloc[i].name[2]}' )

    total_min = 200
    total_max = 1500
    cdf_list = []
    for i in range(len(input_tif_file_list)):
        hist, bins= np.histogram(m_reshape_list[i], bins = np.linspace(total_min,total_max,(total_max-total_min)/h_step), density = True)
        cdf = np.cumsum(hist)*h_step
        cdf_list.append(cdf)
        ax[0].plot(bins[0:-1],hist, color=colors[i])
        ax[1].plot(bins[0:-1],cdf, color=colors[i])

    ax[0].set_xlabel('Pixel Intensity')
    ax[1].set_xlabel('Pixel Intensity')
    ax[0].set_ylabel('Density')
    ax[1].set_ylabel('CDF')
    ax[0].legend((legend))
    fig.savefig(output_steps_file_path + '.png')

    # Concatenate them using the concat function
    m_concat = cm.concatenate(m_list, axis=0)
    data_dir = 'data/interim/alignment/main'
    file_name = db.create_file_name(step_index, index)
    fname= m_concat.save(data_dir  + '/' + file_name + '_pw_rig' + '.mmap', order='C')

    cdf_m = np.ma.masked_equal(cdf, 0)
    cdf_m = (cdf_m - cdf_m.min()) * 255 / (cdf_m.max() - cdf_m.min())
    cdf = np.ma.filled(cdf_m, 0).astype('uint8')

    #meta_pkl_dict['pw_rigid']['cropping_points'] = [x_, _x, y_, _y]
    #output['meta']['cropping_points'] = [x_, _x, y_, _y]
    # Save the movie
    #fname_tot_els  = m_els.save(data_dir + 'main/' + file_name + '_els' + '.mmap',  order='C')
    #logging.info(f'{index} Cropped and saved rigid movie as {fname_tot_els}')

    # MOTION CORRECTING EACH INDIVIDUAL MOVIE WITH RESPECT TO A TEMPLATE MADE OF THE FIRST MOVIE
    logging.info(f'{alignment_index} Performing motion correction on all movies with respect to a template made of \
    the first movie.')
    t0 = datetime.datetime.today()

    # Create a template of the first movie
    template_index = trial_index_list.index(parameters['make_template_from_trial'])
    m0 = cm.load(input_mmap_file_list[template_index ])
    [x1, x2, y1, y2] = motion_correction_output_list[template_index]['meta']['cropping_points']
    m0 = m0.crop(new_x1 - x1, new_x2 - x2, new_y1 - y1, new_y2 - y2, 0, 0)
    m0_filt = cm.movie(
        np.array([high_pass_filter_space(m_, parameters['gSig_filt']) for m_ in m0]))
    template0 = cm.motion_correction.bin_median(
        m0_filt.motion_correct(5, 5, template=None)[0])  # may be improved in the future

    # Setting the parameters
    opts = params.CNMFParams(params_dict=parameters)

    # Create a motion correction object
    mc = MotionCorrect(fname, dview=dview, **opts.get_group('motion'))

    # Perform non-rigid motion correction
    mc.motion_correct(template=template0, save_movie=True)

    # Cropping borders
    x_ = math.ceil(abs(np.array(mc.shifts_rig)[:, 1].max()) if np.array(mc.shifts_rig)[:, 1].max() > 0 else 0)
    _x = math.ceil(abs(np.array(mc.shifts_rig)[:, 1].min()) if np.array(mc.shifts_rig)[:, 1].min() < 0 else 0)
    y_ = math.ceil(abs(np.array(mc.shifts_rig)[:, 0].max()) if np.array(mc.shifts_rig)[:, 0].max() > 0 else 0)
    _y = math.ceil(abs(np.array(mc.shifts_rig)[:, 0].min()) if np.array(mc.shifts_rig)[:, 0].min() < 0 else 0)

    dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
    output['meta']['duration']['motion_correction'] = dt
    logging.info(f'{alignment_index} Performed motion correction. dt = {dt} min.')


    # Create a timeline and store it
    timeline = [[trial_index_list[0], 0]]
    for i in range(1, len(m_list)):
        m = m_list[i]
        timeline.append([trial_index_list[i], timeline[i - 1][1] + m.shape[0]])
    #    timeline_pkl_file_path = f'data/interim/alignment/meta/timeline/{file_name}.pkl'
    #    with open(timeline_pkl_file_path,'wb') as f:
    #        pickle.dump(timeline,f)
    #    output['meta']['timeline'] = timeline_pkl_file_path
    output['meta']['timeline'] = timeline

    # Save the concatenated movie
    output_mmap_file_path_tot = m_concat.save(output_mmap_file_path, order = 'C')
    output['main'] = output_mmap_file_path_tot

    #    # Delete the motion corrected movies
    #    for fname in mc.fname_tot_rig:
    #        os.remove(fname)

    dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
    output['meta']['duration']['concatenation'] = dt
    logging.info(f'{alignment_index} Performed concatenation. dt = {dt} min.')

    for idx, row in df.iterrows():
        df.loc[idx, 'alignment_output'] = str(output)
        df.loc[idx, 'alignment_parameters'] = str(parameters)

    return df
