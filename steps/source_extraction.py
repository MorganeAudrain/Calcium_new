# -*- coding: utf-8 -*-

import datetime
import data_base_manipulation as db
import analysis_files_manipulation as fm

import caiman as cm 
from caiman.source_extraction import cnmf
from caiman.source_extraction.cnmf import params as params

import caiman.base.rois
import logging

import numpy as np 
import os
import psutil

#step = 'source_extraction'

#%% MAIN
def run_source_extraction(row, parameters, dview, session_wise = False):
    '''
    This is the function for source extraction.
    Its goal is to take in a .mmap file,
    perform source extraction on it using cnmf-e and save the cnmf object as a .pkl file.    
    
    This function is only runnable on the cn76 server because it requires parralel processing. 
    
    Args:
        row: pd.DataFrame object
            The row corresponding to the analysis state to be source extracted. 
            
    Returns:
        row: pd.DataFrame object
            The row corresponding to the source extracted analysis state.   
    '''
    step_index = 4
    row_local = row.copy()
    row_local.loc['source_extraction_parameters'] = str(parameters)
    row_local = db.set_version_analysis('source_extraction',row_local,session_wise)
    index = row_local.name

    # Determine input path
    if parameters['session_wise']:
        input_mmap_file_path = eval(row_local.loc['alignment_output'])['main']
    else: 
        input_mmap_file_path = eval(row_local.loc['motion_correction_output'])['main']
    if not os.path.isfile(input_mmap_file_path):
        logging.error('Input file does not exist. Cancelling.')
        return row_local
    
    # Determine output paths
    file_name = db.create_file_name(step_index, index)
    data_dir = 'data/interim/source_extraction/session_wise/' if parameters['session_wise'] else 'data/interim/source_extraction/trial_wise/'
    output_file_path = data_dir + f'main/{file_name}.hdf5'
   
        
    # Create a dictionary with parameters
    output = {
            'main': output_file_path,
            'meta':{
                'analysis' : {
                        'analyst' : os.environ['ANALYST'],
                        'date' : datetime.datetime.today().strftime("%m-%d-%Y"),
                        'time' : datetime.datetime.today().strftime("%H:%M:%S"),
                        },
                    'duration': {}
                    }
                }
    
    # Load memmory mappable input file
    if os.path.isfile(input_mmap_file_path):
        Yr, dims, T = cm.load_memmap(input_mmap_file_path)
#        logging.debug(f'{index} Loaded movie. dims = {dims}, T = {T}.')
        images = Yr.T.reshape((T,) + dims, order='F')
    else:
        logging.warning(f'{index} .mmap file does not exist. Cancelling')
        return row_local
    
    # SOURCE EXTRACTION
    # Check if the summary images are already there
    corr_npy_file_path, pnr_npy_file_path = fm.get_corr_pnr_path(index, gSig_abs = parameters['gSig'][0])
    
    if corr_npy_file_path != None and os.path.isfile(corr_npy_file_path):  
        # Already computed summary images
        logging.info(f'{index} Already computed summary images')
        cn_filter = np.load(corr_npy_file_path)
        pnr = np.load(pnr_npy_file_path)
    else:
        # Compute summary images
        t0 = datetime.datetime.today()
        logging.info(f'{index} Computing summary images')
        cn_filter, pnr = cm.summary_images.correlation_pnr(images[::1], gSig = parameters['gSig'][0], swap_dim=False)
        dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
        output['meta']['duration']['summary_images'] = dt 
        logging.info(f'{index} Computed summary images. dt = {dt} min')
        # Saving summary images as npy files
        gSig = parameters['gSig'][0]
        corr_npy_file_path = data_dir + f'/meta/corr/{db.create_file_name(3, index)}_gSig_{gSig}.npy'
        pnr_npy_file_path = data_dir + f'/meta/pnr/{db.create_file_name(3, index)}_gSig_{gSig}.npy'
        with open(corr_npy_file_path, 'wb') as f:
            np.save(f, cn_filter)
        with open(pnr_npy_file_path, 'wb') as f:
            np.save(f, pnr)
    
    # Store the paths in the meta dictionary 
    output['meta']['corr'] = {'main': corr_npy_file_path, 'meta': {}}
    output['meta']['pnr'] = {'main': pnr_npy_file_path, 'meta': {}}
    
    # Calculate min, mean, max value for cn_filter and pnr
    corr_min, corr_mean, corr_max = cn_filter.min(), cn_filter.mean(), cn_filter.max()
    output['meta']['corr']['meta'] = {'min': corr_min, 'mean': corr_mean, 'max': corr_max}
    pnr_min, pnr_mean, pnr_max = pnr.min(), pnr.mean(), pnr.max()
    output['meta']['pnr']['meta'] = {'min': pnr_min, 'mean': pnr_mean, 'max': pnr_max}
    
    # If min_corr and min_pnr are specified via a linear equation, calculate 
    # this value 
    if type(parameters['min_corr']) == list:
        min_corr = parameters['min_corr'][0]*corr_mean + parameters['min_corr'][1]
        parameters['min_corr'] = min_corr
        logging.info(f'{index} Automatically setting min_corr = {min_corr}')
    if type(parameters['min_pnr']) == list:
        min_pnr =  parameters['min_pnr'][0]*pnr_mean + parameters['min_pnr'][1]
        parameters['min_pnr'] = min_pnr
        logging.info(f'{index} Automatically setting min_pnr = {min_pnr}')

    # Set the parameters for caiman
    opts = params.CNMFParams(params_dict = parameters)   
    
    # SOURCE EXTRACTION 
    logging.info(f'{index} Performing source extraction')
    t0 = datetime.datetime.today()
    n_processes = psutil.cpu_count()
    logging.info(f'{index} n_processes: {n_processes}')
    cnm = cnmf.CNMF(n_processes = n_processes, dview = dview, params = opts)
    cnm.fit(images)
    cnm.estimates.dims = dims    
    
    # Store the number of neurons
    output['meta']['K'] = len(cnm.estimates.C)
    
    # Calculate the center of masses
    cnm.estimates.center = caiman.base.rois.com(cnm.estimates.A, images.shape[1], images.shape[2])
    
    # Save the cnmf object as a hdf5 file 
    logging.info(f'{index} Saving cnmf object')
    cnm.save(output_file_path)
    dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
    output['meta']['duration']['source_extraction'] = dt
    logging.info(f'{index} Source extraction finished. dt = {dt} min')
    
    # Write necessary variables in row and return
    row_local.loc['source_extraction_parameters'] = str(parameters)
    row_local.loc['source_extraction_output'] = str(output)
        
    return row_local
