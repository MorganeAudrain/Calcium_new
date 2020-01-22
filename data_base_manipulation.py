#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 12 12:00:12 2019

@author: Sebastian, Casper and Melisa

Functions in this file are related to data base manipulation, open pandas dataframe, selection of data to analyze,
setting of version analysis state in data base, parameter setting and getting for the parameter data base.

"""

import os
import logging
import pandas as pd
import configparser
import collections
import math
import datetime
import shutil
import numpy as np

import paths as paths
import server as connect

steps = [
        'decoding', 
        'cropping', # spatial borders that are unusable (due to microenscope border 
        # or blood clot) are removed
        'motion_correction', # individual trial movies (5 min) are rigidly or 
        # piecewise rigidly motion corrected
        'alignment', # Multiple videos (e.g. all trials of a session, 210 min) are
        # rigid motion corrected to each other, resulting in a long aligned video
        'source_extraction', # neural activity is deconvolved from the videos
        # trial-wise or session-wise
        'component_evaluation'
        ]

def get_step_index(step):
    '''
    This function returns the step index (int) given
    a step name (str)
    '''
    try:
        return steps.index(step)  
    except:
        logging.error(f'Not a valid step. Valid values are: {steps}')
        return


def get_query_from_dict(dictionary):
    query = ''
    for key in dictionary:
        if dictionary[key] == None:
            logging.warning('There is a None in the dictionary. None s are not allowed!')
        if query != '':
            query += ' & '
        query += f'{key} == {dictionary[key]}'
    return query


def get_data_name(index):
    return f'mouse_{index[0]}_session_{index[1]}_trial_{get_trial_name(index[2],index[3])}'

def get_trial_name(trial, is_rest):
    return f'{trial}' if is_rest == 0 else f'{trial}_R'


def get_file(path):
    '''
    Universal function to obtain files. It checks if the file exists. If it is
    on the local machine and the file doesn't exist, it tries to download the file.

    Args:
        path: str
            Path with respect to project directory
    '''
    if bool(os.environ['LOCAL']):
        if os.path.isfile(path):
            return path
        else:
            logging.warning('File does not exist locally')
            try:
                connect.download(path)
                return path
            except IOError:
                logging.error('File does not exist on the server either!')
    else:
        if os.path.isfile(path):
            return path
        else:
            logging.error('File does not exist on server')


def create_file_name(step_index, index):
    '''
    This function returns a correct basename used for files
    (str, e.g. "mouse_56166_session_2_trial_1_R_v1.3.1")
    given an analysis state index and a step_index
    '''
    # Make the string corresponding to the trial (_R for rest trials)
    trial_R_string = f'{index[2]}_R' if index[3] else f'{index[2]}'
    trial_string = f"mouse_{index[0]}_session_{index[1]}_trial_{trial_R_string}"
    analysis_version_string = 'v'
    for i in range(0, step_index + 1):
        if i != 0:
            analysis_version_string += '.'
        analysis_version_string += str(index[4 + i])
    filename = f'{trial_string}_{analysis_version_string}'
    return filename

def dict_compare(d1, d2):
    '''
    This function compares two dictionaries
    :param d1: first dictionary
    :param d2: second dictionary
    :return:
    '''
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o : (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return added, removed, modified, same


def replace_at_index1(tup, ix, val):
    lst = list(tup)
    lst[ix] = val
    return tuple(lst)

def set_version_analysis(step,row ,session_wise = False):

    '''
    This function checks whether the parameters selected for a particular step had already been used to do the analysis.
    If they had been used, it does nothing. If they had not been used already it created a new identity (name) for the row
    updating the version to number of versions+1.
    :param step: pipeline step
    :param states_df: data base state.
    :param row: particular row with parameters for all steps (one line in the database)
    :param session_wise: flag to indicate whether the run is trial_wise or session_wise. By default it is False
            This in important for version setting of steps that goes after alignment.
    :return: row_local, a copy of row but with new version setting.
    '''
    states_df = open_analysis_states_database()
    step_index = get_step_index(step)
    index = row.name
    row_local = row.copy()
    if step_index > 0:

        # Select the specified data
        data_criteria_0 = [index[0], index[1],index[2], index[3]]
        data_criteria = {paths.data_structure[i]: data_criteria_0[i] for i in range(0, len(paths.data_structure)) if
                         data_criteria_0[i] != None}
        query = get_query_from_dict(data_criteria)
        if query != '':
            logging.debug('Selecting rows corresponding to specified data')
            logging.debug('query: ' + query)
            selected_rows = states_df.query(query)
            logging.debug(f'{len(selected_rows)} rows found')
        else:
            selected_rows = states_df

        # Select the specified analysis version
        analysis_criteria_0 = [index[4], index[5], index[6], index[7], index[8], None]
        for ii in range(step_index,len(analysis_criteria_0)):
            analysis_criteria_0[ii]=None
        analysis_criteria = {paths.analysis_structure[i]: analysis_criteria_0[i] for i in
                             range(0, len(paths.analysis_structure)) if analysis_criteria_0[i] != None}
        query = get_query_from_dict(analysis_criteria)
        if query != '':
            logging.debug('Selecting rows corresponding to specified data')
            logging.debug('query: ' + query)
            selected_rows = selected_rows.query(query)
            logging.debug(f'{len(selected_rows)} rows found')

        query_list_current = []
        if session_wise or step_index < 3:
            for ii in steps[:step_index + 1]:
                if step != 'alignment':
                    query_list_current.append(f'{ii}_v != 0')
            for ii in steps[step_index + 1:]:
                query_list_current.append(f'{ii}_v == 0')
            query = ' and '.join(query_list_current)
            logging.debug(f'Selecting rows with a non-zero input analysis version. Query: \n {query}')
            selected_rows= selected_rows.query(query)
            logging.debug(f'{len(selected_rows)} rows found')

            # If no trials were found.
            if selected_rows.empty:
                logging.warning(f'No rows were found for the specified parameters.')
        else:
            if step_index == 4:
                for ii in steps[:step_index -1]:
                    query_list_current.append(f'{ii}_v != 0')
                query_list_current.append(f'{step}_v != 0')
                for ii in steps[step_index + 1:]:
                    query_list_current.append(f'{ii}_v == 0')
                query = ' and '.join(query_list_current)
                logging.debug(f'Selecting rows with a non-zero input analysis version. Query: \n {query}')
                selected_rows= selected_rows.query(query)
                logging.debug(f'{len(selected_rows)} rows found')
                # If no trials were found.
                if selected_rows.empty:
                    logging.warning(f'No rows were found for the specified parameters.')
            else:
                for ii in steps[:step_index-2]:
                    query_list_current.append(f'{ii}_v != 0')
                for ii in steps[step_index - 1: step_index+1]:
                    query_list_current.append(f'{ii}_v != 0')
                query = ' and '.join(query_list_current)
                logging.debug(f'Selecting rows with a non-zero input analysis version. Query: \n {query}')
                selected_rows= selected_rows.query(query)
                logging.debug(f'{len(selected_rows)} rows found')
                # If no trials were found.
                if selected_rows.empty:
                    logging.warning(f'No rows were found for the specified parameters.')

        max_versions = len(selected_rows)
        verified_parameters = 0
        for ii in range(0,max_versions):
            version = selected_rows.iloc[ii]
            a,b,c,d = dict_compare(eval(version[f'{step}'+'_parameters']),eval(row_local[f'{step}'+'_parameters']))
            if bool(c):
                verified_parameters = verified_parameters +1
            else:
                new_index = version.name
        if verified_parameters == max_versions:
            new_index = replace_at_index1(index, 4 + step_index, max_versions+1)
    else:
        new_index = replace_at_index1(index, 4 + step_index, 1)

    row_local.name = new_index
    return row_local

def get_expected_file_path(step, subdirectory, index, extension):
    step_index = get_step_index(step)
    directory = f'data/interim/{step}/' + subdirectory
    if step_index != 2:
        fname = create_file_name(get_step_index(step),index) + extension
    else:
        fname = ''
        expected_fname = create_file_name(get_step_index(step),index)
        for cur_fname in os.listdir(directory):
            if expected_fname in cur_fname:
                fname = cur_fname 
    return directory + fname  


def open_analysis_states_database(path = paths.analysis_states_database_path):
    '''
    This function reads the analysis states database (.xlsx file) using the correct 
    settings as a multi-index dataframe. 
    '''
    if os.getlogin() == 'sebastian':
        logging.info('Downloading analysis states database...')
        ssh = connect.get_SSH_connection()
        sftp = ssh.open_sftp()
        sftp.get(os.environ['PROJECT_DIR_SERVER'] + paths.analysis_states_database_path, os.environ['PROJECT_DIR_LOCAL'] + paths.analysis_states_database_path)
        sftp.close()
        ssh.close()
        logging.info('Downloaded analysis states database')
    
    return pd.read_excel(path,  dtype = {'date' : 'str', 'time' : 'str'}).set_index(paths.multi_index_structure)

def save_analysis_states_database(states_df, path , backup_path):
    '''
    This function writes the analysis states dataframe (states_df) 
    to the analysis states database (.xlsx file).
    '''
    states_df.reset_index().sort_values(by = paths.multi_index_structure)[paths.columns].to_excel(path, index = False)
    
    # Make a backup every day
    make_backup(path, backup_path)

    
    if eval(os.environ['LOCAL']):
        logging.info('Uploading analysis states database...')
        ssh = connect.get_SSH_connection()
        sftp = ssh.open_sftp()
        sftp.put(os.environ['PROJECT_DIR_LOCAL'] + paths.analysis_states_database_path, os.environ['PROJECT_DIR_SERVER'] + paths.analysis_states_database_path)
        sftp.close()
        ssh.close()
        logging.info('Uploaded analysis states database')
    return

def append_to_or_merge_with_states_df(states_df, inp):
    '''
    If the row(s) exist(s) in the analysis states dataframe already, replace it 
    If it doesn't, append it to the analysis states dataframe.
   
    Warning: Getting a fresh copy of the analysis states dataframe and saving it afterwards
    are not part of this function. Add lines before and after this function to 
    do this! 
    
    Args:
        inp: pd.Series object or pd.DataFrame object
            Row(s) to be added to the analysis states dataframe
        states_df: pd.DataFrame object
            Analysis states dataframe to which to append the row
    
    Returns:
        states_df: pd.DataFrame object
            Analysis states dataframe with rows appended
    '''
    
    if str(type(inp)) == "<class 'pandas.core.frame.DataFrame'>":
        # If a dataframe is inserted, apply the function recursively
        for index, row in inp.iterrows():
            states_df = append_to_or_merge_with_states_df(states_df, row)
    else:
        # If a row is inserted
        if inp.name in states_df.index:
            # Replace the row in the analysis states dataframe
            logging.debug(f'Replacing row {inp.name} in analysis states dataframe')
            for item, value in inp.iteritems():
                states_df.loc[inp.name, item] = value
        else:
            logging.debug(f'Appending row {inp.name} to analysis states dataframe')
            # Append it to the analysis states dataframe
            states_df = states_df.append(inp)
            
    return states_df 


def select(states_df, step, mouse = None, session = None, trial = None, is_rest = None,
           decoding_v = None, cropping_v = None, motion_correction_v = None, alignment_v = None,
           source_extraction_v = None, component_evaluation_v = None, max_version = True):
    '''
    This function selects certain analysis states (specified by mouse, session, trial, is_rest,
    decoding_v, cropping_v, etc.) to be used in a certain step.
    If no analysis version is specified, it selects the latest one. 
    It makes sure there only one analysis state per trial. 
    
    This function is quite specialized. Refer to the pandas dataframe.query() method
    for more general selection of analysis states.  
    
    Args:
        states_df database
        step: str
            Determines for which step the states are selected
        
        **kwargs:
            Used to give criteria for the states. May include data criteria
            (e.g. mouse = 32314) or analysis criteria 
            (e.g. motion_correction_v = 3)
    '''
    
    # Get the step index
    step_index = get_step_index(step)
    if not type(step_index) == int:
        # If it is not a valid step, return
        return
    
    # Select the specified data 
    data_criteria_0 = [mouse, session, trial, is_rest]
    data_criteria = {paths.data_structure[i]: data_criteria_0[i] for i in range(0,len(paths.data_structure)) if  data_criteria_0[i] != None}
    query = get_query_from_dict(data_criteria)
    if query != '':
        logging.debug('Selecting rows corresponding to specified data')
        logging.debug('query: ' + query)
        selected_rows = states_df.query(query)
        logging.debug(f'{len(selected_rows)} rows found')
    else:
        selected_rows = states_df


    query_list_previous = []
    for step in steps[:step_index]:
        if step != 'alignment':
            query_list_previous.append(f'{step}_v != 0')
    for step in steps[step_index:]:
        query_list_previous.append(f'{step}_v == 0')
    query = ' and '.join(query_list_previous)
    logging.debug(f'Selecting rows with a non-zero input analysis version. Query: \n {query}')
    selected_rows_previous = selected_rows.query(query)
    logging.debug(f'{len(selected_rows_previous)} rows found')

    query_list_current = []
    for step in steps[:step_index+1]:
        if step != 'alignment':
            query_list_current.append(f'{step}_v != 0')
    for step in steps[step_index+1:]:
        query_list_current.append(f'{step}_v == 0')
    query = ' and '.join(query_list_current)
    logging.debug(f'Selecting rows with a non-zero input analysis version. Query: \n {query}')
    selected_rows_current = selected_rows.query(query)
    logging.debug(f'{len(selected_rows_current)} rows found')

    selected_rows = append_to_or_merge_with_states_df(selected_rows_previous,selected_rows_current)

    # Select the specified analysis version  
    analysis_criteria_0 = [decoding_v, cropping_v, motion_correction_v, alignment_v, source_extraction_v, component_evaluation_v]
    analysis_criteria = {paths.analysis_structure[i]: analysis_criteria_0[i] for i in range(0,len(paths.analysis_structure)) if  analysis_criteria_0[i] != None}
    query = get_query_from_dict(analysis_criteria)
    if query != '':
        logging.debug('Selecting rows corresponding to specified data')
        logging.debug('query: ' + query)
        selected_rows =selected_rows.query(query)
        logging.debug(f'{len(selected_rows)} rows found')

    if max_version:
        #Make sure there is only one row per trial
        logging.debug('Making sure there is only one row per trial.')
        for trial_index, trial_frame in selected_rows.groupby(level = paths.data_structure):
            # Determine the latest input step version per trial
            sorted_frame = trial_frame.sort_values(paths.analysis_structure).reset_index()
            best_row = sorted_frame.loc[len(sorted_frame) - 1]
            best_row_analysis_index = tuple((best_row.loc[j] for j in paths.analysis_structure))
            best_row_index = trial_index + best_row_analysis_index
            # Now drop all failed rows from that frame
            for row_index, row in trial_frame.iterrows():
                if row_index != best_row_index:
                    selected_rows = selected_rows.drop(row_index)
        logging.debug(f'{len(selected_rows)} rows found')

    # If no trials were found.
    if selected_rows.empty:
        logging.warning(f'No rows were found for the specified parameters.')
        
    return selected_rows     


def convert_OrderedDict_to_Dict(OrderedDict):
    '''
    This recursive function converts and ordered dictionary 
    to a regular one whilst evaluating its contents. It's useful for 
    reading config files.
    '''
    for item in OrderedDict:
        if isinstance(item, OrderedDict):
            return convert_OrderedDict_to_Dict(item)
        else:
            return eval(item)
        
def remove_None_from_dict(dictionary):
    ''' This function removes None's from dictionary'''
    filtered_dictionary = {}
    for key in dictionary:
        if type(dictionary[key]) != type(None):
            filtered_dictionary[key] = dictionary[key]
    return filtered_dictionary 
        

def get_config(config_file_path):
    '''
    This function reads a config file and converts it 
    to a dictionary using "convert_OrderedDict_to_Dict".
    '''
    c = configparser.ConfigParser()
    c.read(config_file_path)
    return convert_OrderedDict_to_Dict(c.__sections)
                                                            

def get_parameters(step, mouse = None, session = None, trial = None, is_rest = None, download_ = True):
    '''
    This function gets the parameters set for a certain trial (specified by mouse,
    session, trial, is_rest) by the parameters database. 
    
    Args:
        step: str
            The step to which the parameters belong
        mouse, session, trial, is_rest: int
            Used to specify a certain piece of the data. 
        download_: bool
            Whether or not to download the parameters database from the server
            before reading the local copy. 
    
    Returns:
        params: dict
            A dictionary containing the parameters.     
    '''
    
    if os.getlogin() == 'sebastian' and download_:
        logging.debug('Downloading parameters...')
        ssh = connect.get_SSH_connection()
        sftp = ssh.open_sftp()
        sftp.get( os.environ['PROJECT_DIR_SERVER'] + paths.parameters_path, os.environ['PROJECT_DIR_LOCAL'] + paths.parameters_path)
        sftp.close()
        ssh.close()
    
    
    df = pd.read_excel(paths.parameters_path, sheet_name = step)
    
    # Determine the parameters
    param_names = [p for p in df.columns.tolist() if p not in (['type', 'comment'] + paths.data_structure)]
    
    # Store the default parameters
    params =  dict(df.query('type == "default"').iloc[0][param_names]) 
    dtypes =  dict(df.query('type == "dtype"').iloc[0][param_names]) 
#    logging.debug(f'The following default parameters were found: {params}')
    
    # Look for parameters specific to that mouse, session or trial 
    criteria = [mouse, session, trial, is_rest]
    for i, criterium in enumerate(criteria):
        if criterium != None:
            query_dict = {paths.data_structure[j] : criteria[j] for j in range(0, i + 1)}
            query = get_query_from_dict(query_dict)
#            logging.debug(f'Looking for specific parameters to {data_structure[i]} using query: \n {query}')
            selected_rows = df.query(query)
            selected_rows = selected_rows[selected_rows.isnull()[paths.data_structure[i + 1:]].T.all().T]

            if not selected_rows.empty:
                # If specific parameters are found, apply them 
#                logging.debug(f'Found parameters specific to {data_structure[i]}: \n {selected_rows}')
                params_update = dict(selected_rows.iloc[0][param_names])
#                logging.debug(f'params_update: {params_update}')
                new_update = {}
                for key in params_update:
                    if type(params_update[key]) == str or not math.isnan(params_update[key]):
                        new_update[key] = params_update[key]
                if len(new_update) != 0:
                    params.update(new_update) 
#                logging.debug(f'params after update: {params}')
    
    # Evaluate the parameters (e.g. turn 'True' into True)
    for key in param_names:
#        if not eval(dtypes[key]) == type(params[key]):
#            params[key] = eval(dtypes[key] + f'({params[key]})')    
#        
        if dtypes[key] == 'boolean':
            params[key] = bool(params[key])
        elif dtypes[key] == 'str':
            params[key] = str(params[key])
        else:
            try:
                params[key] = eval(params[key])
            except:
                pass

    return params
    
    

def set_parameters(step, params, mouse = None, session = None, trial = None, 
                   is_rest = None, check = True, upload_ = True):
    '''
    This function sets the parameters set for a certain trial (specified by mouse,
    session, trial, is_rest) in the parameters database. 
    
    Args:
        step: str
            The step to which the parameters belong
        mouse, session, trial, is_rest: int
            Used to specify a certain piece of the data. 
        check: bool
            Whether or not to ask for a final confirmation in the console
        upload_: bool
            Whether or not to upload the parameters database to the server
            after writing to the local copy.    
    '''
    

    criteria = [mouse, session, trial, is_rest]
    query_dict = {paths.data_structure[j] : criteria[j] for j in range(0, 4) if not criteria[j] == None}
    
    # Load parameters dataframe
    read = pd.ExcelFile(paths.parameters_path)
    df_dict = {}
    for sheet_name in read.sheet_names:
        df_dict[sheet_name] = pd.read_excel(paths.parameters_path, sheet_name = sheet_name) 
    df = df_dict[step]
    read.close()

    if mouse != None:
        if check:
            print(f'Set the following parameters for {query_dict}? \n {params}')
            cont = ''
            while cont != 'yes' and  cont != 'no':
                print("Type 'yes' or 'no'")
                cont = input()
            if cont == 'no':
                print('Cancelling')
                return
        print(f'Setting parameters for {query_dict} \n {params}')
                
        # Check if there already is a row with these criteria
        query = get_query_from_dict(query_dict)
        selected_rows = df.query(query)
    
        if not selected_rows.empty:
            for idx, row in selected_rows.iterrows():
                for key in params:
                    df.loc[idx, key] = str(params[key]) if isinstance(params[key], collections.Sequence) else params[key]
        else: 
            params.update(query_dict)
            df = df.append(params, ignore_index = True)
            
        print(f'Set parameters for {query_dict} \n {params}')
    else:
        if check:
            print(f'Set the following parameters as default? \n {params}')
            cont = ''
            while cont != 'yes' and  cont != 'no':
                print("Type 'yes' or 'no'")
                cont = input()
            if cont == 'no':
                print(f'Cancelling')
                return
        print(f'Setting parameters as default: \n {params}')
        
        selected_rows = df.query('type == "default"')
        
        for idx, row in selected_rows.iterrows():
                for key in params:
                    df.loc[idx, key] = str(params[key]) if isinstance(params[key], collections.Sequence) else params[key]

    df_dict[step] = df
    with pd.ExcelWriter(paths.parameters_path) as writer:
        for key in df_dict:
            df_dict[key].to_excel(writer, sheet_name=key, index = False)
            
    # Make a backup every day
    make_backup(paths.parameters_path,paths.backup_path)
    
    if eval(os.environ['LOCAL']) and upload_:
        connect.upload(paths.parameters_path)

    return

def make_backup(file_path, backup_dir):
    ''' 
    This function backs up a certain file if no back-up
    exists of that day.
    
    Args:
        file_path: str
            Path of the file to be backed up
        backup_dir: str
            Directory in which back-ups are stored
    ''' 
    date = datetime.datetime.today().strftime("%m_%d_%Y")
    backup_file_name = os.path.splitext(os.path.split(file_path)[-1])[-2] + f'_{date}' + os.path.splitext(file_path)[-1]
    if not backup_file_name in os.listdir(backup_dir):
        shutil.copy(file_path, backup_dir + backup_file_name)
    return

#%% MOVIES
    
def crop_movies_for_concatenation(m_list, axis):
    ''' 
    This function crops movies such that they can be concatenated.


    Args:
        m_list: list
            List of movies to be cropped (caiman.movie object)
        axis: int
            Axis along which the movies are to be cropped
    Returns:
        m_list: list
            List of cropped movies
    '''
    for i in [0,1,2]:
        if i != axis:
            minimum = min([m.shape[i] for m in m_list])
            for j, m in enumerate(m_list):
                if m.shape[i] != minimum:
                    d = m.shape[i] - minimum 
                    if i == 0:
                        m_list[j] = m.crop(0,0,0,0,0,d)
                    elif i == 1:
                        m_list[j] = m.crop(0,d,0,0,0,0)
                    elif i == 2:
                        m_list[j] = m.crop(0,0,0,d,0,0)
    return m_list


def crop_movies_to_clips(m_list, clip_length):
    m_cropped_list = []
    for m in m_list:
        m_cropped_list.append(m.crop(0,0,0,0,0,m.shape[0]-clip_length))
    return m_cropped_list


# %% FILES

def get_file(path):
    '''
    Universal function to obtain files. It checks if the file exists. If it is
    on the local machine and the file doesn't exist, it tries to download the file.

    Args:
        path: str
            Path with respect to project directory
    '''
    if bool(os.environ['LOCAL']):
        if os.path.isfile(path):
            return path
        else:
            logging.warning('File does not exist locally')
            try:
                download(path)
                return path
            except IOError:
                logging.error('File does not exist on the server either!')
    else:
        if os.path.isfile(path):
            return path
        else:
            logging.error('File does not exist on server')

