# -*- coding: utf-8 -*-
"""
@author: Sebastian,Casper
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

step_index = 3


def run_alignmnet(states_df, parameters, dview):
    '''
    This is the main function for the alignment step. It applies methods
    from the CaImAn package used originally in motion correction
    to do alignment.

    Args:
        df: pd.DataFrame
            A dataframe containing the analysis states you want to have aligned.
        parameters: dict
            The alignment parameters.
        dview: object
            The dview object

    Returns:
        df: pd.DataFrame
            A dataframe containing the aligned analysis states.
    '''

    # Sort the dataframe correctly
    df = states_df.copy()
    df = df.sort_values(by=paths.multi_index_structure)

    # Determine the mouse and session of the dataset
    index = df.iloc[0].name
    mouse, session, *r = index
    # alignment_v = index[len(paths.data_structure) + step_index]
    alignment_v = len(df)
    alignment_index = (mouse, session, alignment_v)

    # Determine the output .mmap file name
    file_name = f'mouse_{mouse}_session_{session}_v{alignment_v}'
    output_mmap_file_path = f'data/interim/alignment/main/{file_name}.mmap'

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
    motion_correction_parameters_list = []
    motion_correction_output_list = []
    input_mmap_file_list = []
    trial_index_list = []
    x_ = []
    _x = []
    y_ = []
    _y = []
    for idx, row in df.iterrows():
        motion_correction_parameters_list.append(eval(row.loc['motion_correction_parameters']))
        motion_correction_output = eval(row.loc['motion_correction_output'])
        motion_correction_output_list.append(motion_correction_output)
        input_mmap_file_list.append(motion_correction_output['main'])
        trial_index_list.append(db.get_trial_name(idx[2], idx[3]))
        [x1,x2,y1,y2] = motion_correction_output['meta']['cropping_points']
        x_.append(x1)
        _x.append(x2)
        y_.append(y1)
        _y.append(y2)

    new_x1 = max(x_)
    new_x2 = max(_x)
    new_y1 = max(y_)
    new_y2 = max(_y)
    m_list = []
    legend = []
    a=[]
    for i in range(len(input_mmap_file_list)):
        m = cm.load(input_mmap_file_list[i])
        motion_correction_output = eval(df.iloc[i].loc['motion_correction_output'])
        [x1,x2,y1,y2] = motion_correction_output['meta']['cropping_points']
        m = m.crop(new_x1 - x1, new_x2 - x2, new_y1 - y1, new_y2 - y2, 0, 0)
        m_list.append(m)
        reshape_m = np.reshape(m, (m.shape[0] * m.shape[1] * m.shape[2]))
        _ = plt.hist(reshape_m, bins='auto', density = True)  # arguments are passed to np.histogram
        legend.append('trial = ' + f'{df.iloc[i].name[2]}' )
        x = np.histogram(reshape_m, bins = np.linspace(500,1500,(1500-500)/100),density= True)
        a.append(x[0])
    plt.legend((legend))
    plt.xlabel('Intensity')
    plt.ylabel('Density')

    hist_dir = 'data/interim/alignment/meta/figures/histograms/'
    hist_name = db.create_file_name(3,index)
    plt.savefig(hist_dir + hist_name + '.png')
    plt.close()

    for i in range(len(a)):
        plt.plot(a[i])

    # Concatenate them using the concat function
    m_concat = cm.concatenate(m_list, axis=0)
    data_dir = 'data/interim/alignment/main'
    file_name = db.create_file_name(step_index, index)
    fname= m_concat.save(data_dir  + '/' + file_name + '_pw_rig' + '.mmap', order='C')

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
