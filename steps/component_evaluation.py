# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
@author: Sebastian,Casper
"""


import datetime
import caiman as cm
import psutil
from caiman.source_extraction.cnmf.cnmf import load_CNMF
import logging
import os

import data_base_manipulation as db

def run_component_evaluation(row, parameters, set_version = None, session_wise = False):

    step_index = 5
    row_local = row.copy()
    row_local.loc['component_evaluation_parameters'] = str(parameters)
    row_local = db.set_version_analysis('component_evaluation',row_local,session_wise)
    index = row_local.name

    motion_correction_output = eval(row_local.loc['motion_correction_output'])
    source_extraction_output = eval(row_local.loc['source_extraction_output'])
    source_extraction_parameters =  eval(row_local.loc['source_extraction_parameters'])
    input_hdf5_file_path = source_extraction_output['main']
    input_mmap_file_path = motion_correction_output['main']
    basename = 'data/interim/component_evaluation/session_wise/' if source_extraction_parameters['session_wise'] else 'data/interim/component_evaluation/trial_wise/'
    file_name = db.create_file_name(step_index, index)
    output_file_path = basename + f'main/{file_name}.hdf5'
    
    if set_version == None:
        # If the output version is not specified, determine it automatically.
        version = index[4 + step_index] + 1
    index = list(index)
    index[4 + step_index] = version
    index = tuple(index)    
    
    
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
    
    # Load CNMF object
    cnm = load_CNMF(input_hdf5_file_path)
    
    # Load the original movie
    Yr, dims, T = cm.load_memmap(input_mmap_file_path)
    images = Yr.T.reshape((T,) + dims, order='F') 

    # Set the parmeters
    cnm.params.set('quality', parameters)


    # Stop the cluster if one exists
    n_processes = psutil.cpu_count()
    try:
        cm.cluster.stop_server()
    except:
        pass

    # Start a new cluster
    c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                     n_processes=n_processes,  # number of process to use, if you go out of memory try to reduce this one
                                                     single_thread=False)
    # Evaluate components
    cnm.estimates.evaluate_components(images, cnm.params, dview=dview)

    logging.debug('Number of total components: ', len(cnm.estimates.C))
    logging.debug('Number of accepted components: ', len(cnm.estimates.idx_components))
    
    # Stop the cluster
    dview.terminate()

    # Save CNMF object
    cnm.save(output_file_path)
    
    # Write necessary variables to the trial index and row
    row_local.loc['component_evaluation_parameters'] = str(parameters)
    row_local.loc['component_evaluation_output'] = str(output)
    
    
    return row_local
