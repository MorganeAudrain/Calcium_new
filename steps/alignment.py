# -*- coding: utf-8 -*-
"""
@author: Sebastian,Casper
"""

import logging
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
    df = df.sort_values(by = paths.multi_index_structure)

    # Determine the mouse and session of the dataset
    index = df.iloc[0].name
    mouse, session, *r = index
    #alignment_v = index[len(paths.data_structure) + step_index]
    alignment_v = len(df)
    alignment_index = (mouse, session, alignment_v)
    
    # Determine the output .mmap file name
    file_name = f'mouse_{mouse}_session_{session}_v{alignment_v}'
    output_mmap_file_path = f'data/interim/alignment/main/{file_name}.mmap'

    try:
        df.reset_index()[['trial','is_rest']].set_index(['trial','is_rest'], verify_integrity = True)
    except ValueError:
        logging.error('You passed multiple of the same trial in the dataframe df')
        return df
    
    output = {
        'meta' : { 
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
    for idx, row in df.iterrows():
        motion_correction_parameters_list.append(eval(row.loc['motion_correction_parameters']) )
        motion_correction_output = eval(row.loc['motion_correction_output'])
        motion_correction_output_list.append(motion_correction_output)
        input_mmap_file_list.append(motion_correction_output['main'])
        trial_index_list.append(db.get_trial_name(idx[2],idx[3]))
    
    # MOTION CORRECTING EACH INDIVIDUAL MOVIE WITH RESPECT TO A TEMPLATE MADE OF THE FIRST MOVIE
    logging.info(f'{alignment_index} Performing motion correction on all movies with respect to a template made of \
    the first movie.')
    t0 = datetime.datetime.today()

    # Create a template of the first movie
    template_index = trial_index_list.index(parameters['make_template_from_trial'])
    m0 = cm.load(input_mmap_file_list[template_index])
    m0_filt = cm.movie(
                np.array([high_pass_filter_space(m_, parameters['gSig_filt']) for m_ in m0]))
    template0 = cm.motion_correction.bin_median(m0_filt.motion_correct(5, 5, template=None)[0]) # may be improved in the future

    # Setting the parameters
    opts = params.CNMFParams(params_dict = parameters)                            													   
    
    # Create a motion correction object 
    mc = MotionCorrect(input_mmap_file_list, dview = dview, **opts.get_group('motion'))
    
    # Perform non-rigid motion correction
    mc.motion_correct(template = template0, save_movie = True)
    
    # Cropping borders
    x_ = math.ceil(abs(np.array(mc.shifts_rig)[:,1].max()) if np.array(mc.shifts_rig)[:,1].max() > 0 else 0)
    _x = math.ceil(abs(np.array(mc.shifts_rig)[:,1].min()) if np.array(mc.shifts_rig)[:,1].min() < 0 else 0)
    y_ = math.ceil(abs(np.array(mc.shifts_rig)[:,0].max()) if np.array(mc.shifts_rig)[:,0].max() > 0 else 0)
    _y = math.ceil(abs(np.array(mc.shifts_rig)[:,0].min()) if np.array(mc.shifts_rig)[:,0].min() < 0 else 0)
    
    dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
    output['meta']['duration']['motion_correction'] = dt
    logging.info(f'{alignment_index} Performed motion correction. dt = {dt} min.')
    
    # CONCATENATING ALL MOTION CORRECTED MOVIES
    logging.info(f'{alignment_index} Concatenating all motion corrected movies.')
    
    # Load all movies into memory    
    m_list = [cm.load(fname) for fname in mc.fname_tot_rig]
    
    # Crop all movies to those border pixels
    for idx, m in enumerate(m_list):
        m_list[idx] = m.crop(x_,_x,y_,_y,0,0)
    output['meta']['cropping_points'] = [x_,_x,y_,_y]
        
    # Concatenate them using the concat function 
    m_concat = cm.concatenate(m_list, axis = 0)
    
    # Create a timeline and store it
    timeline = [[trial_index_list[0],0]]
    for i in range(1,len(m_list)):
        m = m_list[i]
        timeline.append([trial_index_list[i], timeline[i-1][1] + m.shape[0]])
#    timeline_pkl_file_path = f'data/interim/alignment/meta/timeline/{file_name}.pkl'
#    with open(timeline_pkl_file_path,'wb') as f:
#        pickle.dump(timeline,f)   
#    output['meta']['timeline'] = timeline_pkl_file_path
    output['meta']['timeline'] = timeline 
  
    # Save the concatenated movie
    output_mmap_file_path_tot = m_concat.save(output_mmap_file_path)
    output['main'] = output_mmap_file_path_tot
    
#    # Delete the motion corrected movies
#    for fname in mc.fname_tot_rig:
#        os.remove(fname)
    
    dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
    output['meta']['duration']['concatenation'] = dt
    logging.info(f'{alignment_index} Performed concatenation. dt = {dt} min.')
    
    for idx, row in df.iterrows():
        df.loc[idx, 'alignment_output'] = str(output)
        df.loc[idx, 'alignment_parameters'] = str(parameters)
 
    return df

#%% METRICS
    
def get_correlations(df):
    '''
    Get the correlation of both the origin movies and the aligned movie w.r.t a template created
    of the movie to which the movies were aligned
    
    Args:
        df: pd.DataFrame
            The dataframe containing the aligned analysis states. 
    
    Returns:
        df: pd.DataFrame
            The dataframe containing the aligned analysis states with
            the metrics stored in the meta output.
    '''
    
    # Load a dummy index
    index = df.iloc[0].name
    
    # Load the original movies and the aligned, concatenated movie
    original_m_list = []
    trial_name_list = [] 
    for index, row in df.iterrows():
        motion_correction_output = eval(row.loc['motion_correction_output'])
        m = cm.load(motion_correction_output['main'])
        original_m_list.append(m)
        trial_name_list.append(db.get_trial_name(index[2],index[3]))
    alignment_output = eval(df.iloc[0].loc['alignment_output'])
    aligned_m = cm.load(alignment_output['main'])
    
    # Load the cropping points and timeline and to which trial the alignment was done 
    cropping_points = alignment_output['meta']['cropping_points']
    timeline = alignment_output['meta']['timeline']
    alignment_parameters = eval(df.iloc[0].loc['alignment_parameters'])
    make_template_from_trial = alignment_parameters['make_template_from_trial']
    template_index = trial_name_list.index(make_template_from_trial)
    
    # Crop the original movies
    cropped_original_m_list = [] 
    for i, m in enumerate(original_m_list):
        [x_, _x, y_, _y] = cropping_points
        cropped_original_m_list.append(m.crop(x_,_x,y_,_y,0,0))
        
    # Concatenate the original movie
    m_original_concat = cm.concatenate(cropped_original_m_list, axis = 0)
    
    # ORIGINAL MOVIE CORRELATIONS
    # Create a template of the movie to which alignment has taken place 
    m0 = cropped_original_m_list[template_index]
    m0_filt = cm.movie(
                np.array([high_pass_filter_space(m_, alignment_parameters['gSig_filt']) for m_ in m0]))
    tmpl = caiman.motion_correction.bin_median(m0_filt.motion_correct(5, 5, template=None)[0]) # may be improved in the future
    # Calculate the correlations of each movie with respect to that template
    logging.debug('Computing original movie correlations')
    t0 = datetime.datetime.today()
    correlations_orig = []
    count = 0
    m_compute = m_original_concat - np.min(m_original_concat)
    for fr in m_compute:
        if count % 100 == 0:
            logging.debug(f'Frame {count}')
        count += 1
        correlations_orig.append(scipy.stats.pearsonr(
            fr.flatten(), tmpl.flatten())[0])
    dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
    logging.debug(f'Computed original movie correlations. dt = {dt} min')
    
    # ALIGNED CORRELATIONS 
    # Create a template of the movie to which alignment has taken place 
    m0 = aligned_m[timeline[template_index][1]:timeline[template_index + 1][1]] if template_index != len(timeline) -1 else aligned_m[timeline[template_index][1]:] 
    m0_filt = cm.movie(
                np.array([high_pass_filter_space(m_, alignment_parameters['gSig_filt']) for m_ in m0]))
    tmpl = caiman.motion_correction.bin_median(m0_filt.motion_correct(5, 5, template=None)[0]) # may be improved in the future

    # Calculate the correlations of each movie with respect to that template
    logging.debug('Computing aligned movie correlations')
    t0 = datetime.datetime.today()
    correlations_aligned = []
    count = 0
    m_compute = aligned_m - np.min(aligned_m)
    for fr in m_compute:
        if count % 100 == 0:
            logging.debug(f'Frame {count}')
        count += 1
        correlations_aligned.append(scipy.stats.pearsonr(
            fr.flatten(), tmpl.flatten())[0])
    dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
    logging.debug(f'Computed aligned movie correlations. dt = {dt} min')    

    # STORE THE CORRELATIONS
    correlations = {'original': correlations_orig, 'aligned': correlations_aligned}
    metrics_pkl_file_path = f'data/interim/alignment/meta/correlations/mouse_{index[0]}_session{index[1]}_v{index[7]}.pkl'
    with open(metrics_pkl_file_path, 'wb') as f:
        pickle.dump(correlations, f)
    alignment_output['meta']['correlations'] = metrics_pkl_file_path
    
    for idx, row in df.iterrows():
        df.loc[idx, 'alignment_output'] = str(alignment_output)
    
    return df 