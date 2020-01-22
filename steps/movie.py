#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 23 15:24:53 2019

@author: melisa
"""

import pandas as pd
import logging
import server as connect
import math

# Paths 
analysis_states_database_path = 'references/analysis/analysis_states_database.xlsx'
backup_path = 'references/analysis/backup/'
parameters_path = 'references/analysis/parameters_database.xlsx'

## GENERAL AUXILIARY FUNCIONS

def get_query_from_dict(dictionary):
    query = ''
    for key in dictionary:
        if dictionary[key] == None:
            logging.warning('There is a None in the dictionary. None s are not allowed!')
        if query != '':
            query += ' & '
        query += f'{key} == {dictionary[key]}'
    return query


## this class only creates a structure where related to the way the data base is structured. 
## It has a method related to the value of the step in interest.
    

class data_structure():
    
    def __init__(self):
        # Define the steps in the pipeline (in order)
        self.steps = [
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

        # Multi Index Structure
        self.data = ['mouse', 'session', 'trial', 'is_rest']
        self.analysis = [f'{step}_v' for step in steps]
        self.data_analysis = self.data+ self.analysis

        # Columns
        self.columns = self.data + ['experiment_parameters', 
            'experiment_comments', 
            'raw_output', 
            'raw_comments']
        # for each step, add a 'v' (version), 'parameters', 'output' and 'comments' columns
        for step in steps:
            self.columns += [f'{step}_{idx}' for idx in ['v','parameters','output','comments']]
        self.columns += ['analyzed_Sebastian'] # whether or not Sebastian has analyzed the data fully    

    def open_database(self, path = analysis_states_database_path):
        '''
        This function reads the analysis states database (.xlsx file) using the correct 
        settings as a multi-index dataframe. 
        '''
        if os.getlogin() == 'sebastian':
            logging.info('Downloading analysis states database...')
            ssh = connect.get_SSH_connection()
            sftp = ssh.open_sftp()
            sftp.get(os.environ['PROJECT_DIR_SERVER'] + path, os.environ['PROJECT_DIR_LOCAL'] + path)
            sftp.close()
            ssh.close()
            logging.info('Downloaded analysis states database')
        
        return pd.read_excel(path,  dtype = {'date' : 'str', 'time' : 'str'}).set_index(self.data_analysis)

                
    def get_step_index(self,step):
        '''
        This function returns the step index (int) given
        a step name (str)
        '''
        try:
            return steps.index(step)  
        except:
            logging.error(f'Not a valid step. Valid values are: {steps}')
            return

class data_configuration():   
    
    def __init__(self, mouse = None, session = None, trial = None, is_rest = None, 
                 decoding_v = None, cropping_v = None,
                 motion_correction_v = None, alignment_v = None, 
                 source_extraction_v = None,component_evaluation_v=None):
        
        self.mouse=mouse
        self.session=session
        self.trial=trial
        self.is_rest=is_rest 
        self.decoding = decoding_v
        self.cropping = cropping_v
        self.motion_correction = motion_correction_v
        self.alignment = alignment_v
        self.sourse_extraction = source_extraction_v
        self.component_evaluation = component_evaluation_v
        
        self.data_structure=data_structure()
    
    def index_assignation(self):
        
        index=(self.mouse,self.session,self.trial,self.is_rest,self.decoding,
               self.cropping, self.motion_correction, self.alignment,
               self.sourse_extraction, self.component_evaluation)
        return index  
    
    def value_assignation(self):
        assignation = {self.data_structure.data[0]:self.mouse, self.data_structure.data[1]:self.session, self.data_structure.data[2]:self.trial, 
                       self.data_structure.data[3]:self.is_rest }
        return assignation
    
    def version_assignation(self):
        assignation = {self.data_structure.analysis[0]:self.decoding, self.data_structure.analysis[1]:self.cropping, self.data_structure.analysis[2]:self.motion_correction, 
                      self.data_structure.analysis[3]:self.alignment,self.data_structure.analysis[4]:self.sourse_extraction,self.data_structure.analysis[5]:self.component_evaluation}
        return assignation
    
    def get_parameters(self, step, path = parameters_path, download_= True):
        '''
        This function gets the parameters set for a certain trial (specified by mouse,
        session, trial, is_rest) by the parameters database. 
        
        Args:
            step: str
                The step to which the parameters belong
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
            sftp.get(os.environ['PROJECT_DIR_SERVER'] + path, os.environ['PROJECT_DIR_LOCAL'] + path)
            sftp.close()
            ssh.close()
        
        step_index = self.data_structure.get_step_index(step)
    
        df = pd.read_excel(path, sheet_name = step_index)
        # Determine the parameters
        param_names = [p for p in df.columns.tolist() if p not in (['type', 'comment'] + self.data_structure.data)]
        
        # Store the default parameters
        params =  dict(df.query('type == "default"').iloc[0][param_names]) 
        dtypes =  dict(df.query('type == "dtype"').iloc[0][param_names]) 
    #    logging.debug(f'The following default parameters were found: {params}')
        
        # Look for parameters specific to that mouse, session or trial 
        criteria = [self.mouse, self.session, self.trial, self.is_rest]
        for i, criterium in enumerate(criteria):
            if criterium != None:
                query_dict = {self.data_structure.data[j] : criteria[j] for j in range(0, i + 1)}
                query = get_query_from_dict(query_dict)
    #            logging.debug(f'Looking for specific parameters to {data_structure[i]} using query: \n {query}')
                selected_rows = df.query(query)
                selected_rows = selected_rows[selected_rows.isnull()[self.data_structure.data[i + 1:]].T.all().T]
    
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



    def set_parameters(self, step, setting_params, path = parameters_path, path_backup = backup_path , check = True, upload_ = True):
        '''
        This function sets the parameters set for a certain trial (specified by mouse,
        session, trial, is_rest) in the parameters database. 
        
        Args:
            step: str
                The step to which the parameters belong
            check: bool
                Whether or not to ask for a final confirmation in the console
            upload_: bool
                Whether or not to upload the parameters database to the server
                after writing to the local copy.    
        '''
        
        query_dict=self.value_assignation()
        #criteria = [self.mouse, self.trial, self.session, self.is_rest] 
        #query_dict = {self.data_structure.data[j] : criteria[j] for j in range(0, 4) if not criteria[j] == None}
        
        # Load parameters dataframe
        read = pd.ExcelFile(path)
        df_dict = {}
        for sheet_name in read.sheet_names:
            df_dict[sheet_name] = pd.read_excel(path, sheet_name = sheet_name) 
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
        with pd.ExcelWriter(path) as writer:
            for key in df_dict:
                df_dict[key].to_excel(writer, sheet_name=key, index = False)
                
        # Make a backup every day
        make_backup(path, path_backup)
        
        if eval(os.environ['LOCAL']) and upload_:
            connect.upload(path)
            
        
    def select(self, step):
        '''
        This function selects certain analysis states (specified by mouse, session, trial, is_rest,
        decoding_v, cropping_v, etc.) to be used in a certain step.
        If no analysis version is specified, it selects the latest one. 
        It makes sure there only one analysis state per trial. 
        
        This function is quite specialized. Refer to the pandas dataframe.query() method
        for more general selection of analysis states.  
        
        Args:
            step: str
                Determines for which step the states are selected
            
            **kwargs:
                Used to give criteria for the states. May include data criteria
                (e.g. mouse = 32314) or analysis criteria 
                (e.g. motion_correction_v = 3)
        '''
        
        # Get the step index
        step_index = self.data_structure.get_step_index(step)
        if not type(step_index) == int:
            # If it is not a valid step, return
            return 
     
        # Open the analysis states dataframe 
        states_df = self.data_structure.open_database()
        
        # Select the specified data 
        query= get_query_from_dict(self.value_assignation())
        
        if query != '':
            logging.debug('Selecting rows corresponding to specified data')
            logging.debug('query: ' + query)
            selected_rows = states_df.query(query)
            logging.debug(f'{len(selected_rows)} rows found')
        else:
            selected_rows = states_df
        
                
        query_list = []
        for ii in self.data_structure.steps[:step_index]: ## for all the steps before current step
            if ii != 'alignment':
                query_list.append(f'{step}_v != 0') 
        for ii in steps[step_index:]:                       ## for all steps that precede current step
            query_list.append(f'{step}_v == 0')
        query = ' and '.join(query_list)
                   
        logging.debug(f'Selecting rows with a non-zero input analysis version. Query: \n {query}')
        selected_rows = selected_rows.query(query)
        logging.debug(f'{len(selected_rows)} rows found')
    
        # Select the specified analysis version  
        #analysis_criteria_0 = [decoding_v, cropping_v, motion_correction_v, alignment_v, source_extraction_v, None]
        #analysis_criteria = {paths.analysis_structure[i]: analysis_criteria_0[i] for i in range(0,len(paths.analysis_structure)) if  analysis_criteria_0[i] != None}
        #query = get_query_from_dict(analysis_criteria)
        
        query= self.version_assignation()
         
            
        # Make sure there is only one row per trial
        logging.debug('Making sure there is only one row per trial.')
        for trial_index, trial_frame in selected_rows.groupby(level = self.data_structure.data):
            # Determine the latest input step version per trial
            sorted_frame = trial_frame.sort_values(self.data_structure.analysis).reset_index()
            best_row = sorted_frame.loc[len(sorted_frame) - 1]
            best_row_analysis_index = tuple((best_row.loc[j] for j in self.data_structure.analysis))
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

        
    def create_file_name(self, step):
        '''
        This function returns a correct basename used for files
        (str, e.g. "mouse_56166_session_2_trial_1_R_v1.3.1")
        given an analysis state index and a step_index 
        '''
        step_index = self.data_structure.get_step_index(step)
        index = self.index_assignation()
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
    

class movie():
    
    ''' 
    This class contains all methods that can be applied to a movie
    
    '''
     
    def __init__(self, step, mouse = None, session = None, trial = None, is_rest = None, 
                 decoding_v = None, cropping_v = None,
                 motion_correction_v = None, alignment_v = None, 
                 source_extraction_v = None,component_evaluation_v=None,
                 selected_rows = None, parameters = None):
        
        self.data=data_configuration(mouse,session,trial,is_rest,decoding_v, cropping_v, 
                                     motion_correction_v, alignment_v, source_extraction_v,component_evaluation_v)
        
        self.step_index = self.data.data_structure.get_step_index(step)
        self.step = step
        self.index = self.data.index_assignation()
        
        self.parameters = self.data.get_parameters(self.step) if self.step_index != 0 else None       
         # If provided, update them with the forced parameters
        if parameters != None:
            self.parameters.update(parameters)
        ## select the state of analysis
        self.selected_rows = self.data.select(self.step)
        # If provided and the rows are a pandas data frame, update them with the selected rows
        if selected_rows != None and type(selected_rows) == pd.core.frame.DataFrame:
            self.selected_rows.update(selected_rows)       
        if self.selected_rows.empty:
            logging.error('No analysis states. Cancelling')
            return
    
      # analysis states dataframe 
   # states_df = db.open_analysis_states_database()


    ## I AM HERE
    
    def version_setting(self):
        
        analysis_version = self.data.version_assignation()
        db_states=self.data.data_structure.open_database()
        
        #if analysis_version[step]== None:
            
            #data_structure_len = len(self.data.data_structure.data)
            #version_len = len(self.data.data_structure.analysis)
            #common_name = db_states.loc[:data_structure_len + self.step_index]
            #max_version = common_name.reset_index().sort_values(by self.data.data_structure.data_analysis[version_len + self.step_index:]).iloc[-1].loc[f'{step}_v']            
            #logging.debug(f'Max. version for step: {step}, input analysis state: {index[:len(variables.data_structure) + step_index]} is {max_version}')
            #index = list(index) ; index[len(variables.data_structure) + step_index] = max_version + 1 ; index = tuple(index) 

    ### this method creates a string with the right name for the file, using mouse, session, trial, is_rest and analysis version information.
    
    def file_handler(self):
        
        # LOGGING
        # create file handler which logs even debug messages
        step_data_dir = f'{self.step}/' if self.step_index != 4 else (f'{self.step}/session_wise/' if self.parameters['session_wise'] else f'{step}/trial_wise/')
        log_file_path = f'data/interim/{step_data_dir}meta/log/{self.data.create_file_name(self.step)}.log'     
        print(log_file_path)   
        
        fh = logging.FileHandler(log_file_path); fh.setLevel(logging.DEBUG)
        # create formatter and add it to the handlers
        formatter = logging.Formatter("%(relativeCreated)12d [%(filename)s:%(funcName)20s():%(lineno)s]"\
                "[%(process)d] %(message)s")
        fh.setFormatter(formatter)
        # add the handlers to the logger
        logging.root.addHandler(fh)        
    
    
    def server_step(self):
        
        server_step_indices = [2,3,4,5]
        
        if self.step_index in server_step_indices: # server step index is defined in this function and is equal 2,3,4,5
            # Cluster mangement for steps performed on the server: motion correction,
            # alignment, source extraction, component evaluation
           
            # Stop the cluster if one exists
            n_processes = psutil.cpu_count()
            cm.cluster.stop_server()   
            # Start a new cluster
            c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                             n_processes=n_processes,  # number of process to use, if you go out of memory try to reduce this one
                                                             single_thread=False)
            logging.info(f'Starting cluster. n_processes = {n_processes}.')
            return c, dview,n_processes


    def confirm_analysis(self,check_rows=None):
        if check_rows:
            # Ask for a final confirmation after selecting analysis states and parameters. 
            print(f'Perform {step} on these states?')
            continue_step = ''
            while continue_step != 'yes' and  continue_step != 'no':
                print("Type 'yes' or 'no'")
                continue_step = input()
            if continue_step == 'no':
                print(f'Cancelling {step}.')
                return
            print(f'Continuing with {step}.')
    
    
    
    def decoding(self,decoding_v):
        
    def cropping(self,decoding_v,cropping_v):
        
    def motion_correction(self,decofing_v,cropping_v,motion_correction_v):
        
    def alignment(self,decofing_v,cropping_v,motion_correction_v,alignment_v):
    
    def source_extraction(self,decofing_v,cropping_v,motion_correction_v,alignment_v,sourse_extraction_v):
        
    def component_evaluation(self,decofing_v,cropping_v,motion_correction_v,alignment_v,sourse_extraction_v,component_evaluation):
        
        