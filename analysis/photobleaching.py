#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  7 15:00:09 2019

@author: sebastian and Casper
modified November 2019 by Melisa
"""

import os
import sys
import numpy as np



# This should be in another file. Let's leave it here for now
sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/')
sys.path.append('/home/sebastian/Documents/Melisa/calcium_imaging_analysis/src/steps/')
sys.path.remove('/home/sebastian/Documents/calcium_imaging_analysis')\
#%% ENVIRONMENT VARIABLES
os.environ['PROJECT_DIR_LOCAL'] = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/'
os.environ['PROJECT_DIR_SERVER'] = '/scratch/mmaidana/calcium_imaging_analysis/'
os.environ['CAIMAN_DIR_LOCAL'] = '/home/sebastian/CaImAn/'
os.environ['CAIMAN_DIR_SERVER'] ='/scratch/mamaidana/CaImAn/'
os.environ['CAIMAN_ENV_SERVER'] = '/scratch/mmaidana/anaconda3/envs/caiman/bin/python'

os.environ['LOCAL_USER'] = 'sebastian'
os.environ['SERVER_USER'] = 'mmaidana'
os.environ['SERVER_HOSTNAME'] = 'cn76'
os.environ['ANALYST'] = 'Meli'

#%% PROCESSING
os.environ['LOCAL'] = str((os.getlogin() == os.environ['LOCAL_USER']))
os.environ['SERVER'] = str(not(eval(os.environ['LOCAL'])))
os.environ['PROJECT_DIR'] = os.environ['PROJECT_DIR_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['PROJECT_DIR_SERVER']
os.environ['CAIMAN_DIR'] = os.environ['CAIMAN_DIR_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['CAIMAN_DIR_SERVER']

import matplotlib.pyplot as plt
import src.data_base_manipulation as db

#%%
#Caiman importation
import caiman as cm
from caiman.utils.visualization import inspect_correlation_pnr
import caiman.source_extraction.cnmf as cnmf
import caiman.base.rois
from caiman.source_extraction.cnmf.cnmf import load_CNMF

import matplotlib.pyplot as plt
from src.steps.component_evaluation import run_component_evaluation as main_component_evaluation

# Paths 
analysis_states_database_path = 'references/analysis/analysis_states_database.xlsx'
backup_path = 'references/analysis/backup/'
parameters_path = 'references/analysis/parameters_database.xlsx'

#%%


## Open thw data base with all data
states_df = db.open_analysis_states_database()
## Select all the data corresponding to a particular mouse. Ex: 56165

#selected_rows = db.select('decoding',56165)

mouse_number = 56165
session = 1
init_trial = 6
end_trial = 11
is_rest = 1

selected_rows = db.select(states_df,'source_extraction',mouse = mouse_number, session = session, is_rest = is_rest,
                          decoding_v= None,
                          cropping_v = 1,
                          motion_correction_v=1,
                          source_extraction_v = 1, alignment_v= 0, max_version= False)
selected_rows = selected_rows.query('trial > 5')

corr_mean_array = []
pnr_mean_array = []
corr_std_array = []
pnr_std_array = []
trial_name_array = []

corr_mean_array_is_rest = []
pnr_mean_array_is_rest = []
corr_std_array_is_rest = []
pnr_std_array_is_rest = []
trial_name_array_is_rest = []

for i in range(len(selected_rows)):
    row = selected_rows.iloc[2*i]
    # Get the index from the row
    index = row.name
    source_extraction_output = eval(row.loc['source_extraction_output'])
    cn_filter = np.load(source_extraction_output['meta']['corr']['main'])
    pnr = np.load(source_extraction_output['meta']['pnr']['main'])
    corr_mean_array = np.append(corr_mean_array, np.mean(cn_filter))
    pnr_mean_array = np.append(pnr_mean_array, np.mean(pnr))
    corr_std_array = np.append(corr_std_array, np.std(cn_filter))
    pnr_std_array = np.append(pnr_std_array, np.std(pnr))
    trial_name_array = np.append(trial_name_array, db.get_trial_name(index[2], index[3]))
    
    row = selected_rows.iloc[2*i+1]
    # Get the index from the row
    index = row.name
    source_extraction_output = eval(row.loc['source_extraction_output'])
    cn_filter = np.load(source_extraction_output['meta']['corr']['main'])
    pnr = np.load(source_extraction_output['meta']['pnr']['main'])
    corr_mean_array_is_rest = np.append(corr_mean_array_is_rest, np.mean(cn_filter))
    pnr_mean_array_is_rest = np.append(pnr_mean_array_is_rest, np.mean(pnr))
    corr_std_array_is_rest = np.append(corr_std_array_is_rest, np.std(cn_filter))
    pnr_std_array_is_rest = np.append(pnr_std_array_is_rest, np.std(pnr))
    trial_name_array_is_rest = np.append(trial_name_array_is_rest, db.get_trial_name(index[2], index[3]))

#%% Plot correlation and peak to noise measures with error bars

vlines = [1,6,] #11,16,22,27,32,37,43]
vlines_session = [1]#,21,43]
corr_y_min=0.2
corr_y_max=0.7
pnr_y_min=0
pnr_y_max=10

linestyle = '--'
fig, axes = plt.subplots(2,2, sharex=True)
fig.set_size_inches(15, 10)
N = len(corr_mean_array)
axes[0][0].vlines(vlines, ymin=corr_y_min, ymax=corr_y_max, color='red', linestyle=linestyle)
axes[0][0].vlines(vlines_session, ymin=corr_y_min, ymax=corr_y_max, color='blue', linestyle=linestyle)
axes[0][0].errorbar(np.arange(1, N+1), corr_mean_array, corr_std_array)
axes[0][0].legend(('TrialDays', 'Testing', 'Corr'))
# axes[0].set_xticks(np.arange(0,N)[::2])
# axes[0].set_xticklabels(trial_name_array[::2])
# axes[0].set_xlabel('trial')
axes[0][0].set_title('correlation')
axes[0][0].set_ylabel('mean')
axes[0][0].set_ylim(corr_y_min, corr_y_max)


axes[1][0].vlines(vlines, ymin=pnr_y_min, ymax=pnr_y_max, color='red', linestyle=linestyle)
axes[1][0].vlines(vlines_session, ymin=pnr_y_min, ymax=pnr_y_max, color='blue', linestyle=linestyle)
axes[1][0].errorbar(np.arange(1, N+1), pnr_mean_array,pnr_std_array, c='orange')
axes[1][0].legend(('TrialDays', 'Testing', 'pnr'))
#axes[1].set_xticks(np.arange(0, N)[::2])
#axes[1].set_xticklabels(trial_name_array[::2])
axes[1][0].set_title('pnr')
axes[1][0].set_ylabel('mean')
axes[1][0].set_xlabel('trial')
axes[1][0].set_ylim(pnr_y_min, pnr_y_max)

axes[0][1].vlines(vlines, ymin=corr_y_min, ymax=corr_y_max, color='red', linestyle=linestyle)
axes[0][1].vlines(vlines_session, ymin=corr_y_min, ymax=corr_y_max, color='blue', linestyle=linestyle)
axes[0][1].errorbar(np.arange(1, N+1), corr_mean_array_is_rest,corr_std_array_is_rest)
# axes[0].set_xticks(np.arange(0,N)[::2])
# axes[0].set_xticklabels(trial_name_array[::2])
# axes[0].set_xlabel('trial')
axes[0][1].set_title('correlation_R')
axes[0][1].set_ylabel('mean')
axes[0][1].set_ylim(corr_y_min, corr_y_max)


axes[1][1].vlines(vlines, ymin=pnr_y_min, ymax=pnr_y_max, color='red', linestyle=linestyle)
axes[1][1].vlines(vlines_session, ymin=pnr_y_min, ymax=pnr_y_max, color='blue', linestyle=linestyle)
#axes[1].vlines(vlines, ymin=4.3, ymax=5.5, color='red', linestyle=linestyle)
axes[1][1].errorbar(np.arange(1, N+1), pnr_mean_array_is_rest, pnr_std_array_is_rest, c='orange')
#axes[1].set_xticks(np.arange(0, N)[::2])
#axes[1].set_xticklabels(trial_name_array[::2])
axes[1][1].set_title('pnr_is_rest')
axes[1][1].set_ylabel('mean')
axes[1][1].set_xlabel('trial')
axes[1][1].set_ylim(pnr_y_min, pnr_y_max)


#axes[1].set_ylim(4.3, 8.2)
plt.subplots_adjust()
fig.savefig('data/interim/source_extraction/trial_wise/meta/figures/fig:corrpnrphotobleaching'+str(56165)+'.png')

#%%  Plot mean correlation

linestyle = '--'
fig, axes = plt.subplots(2,2, sharex=True)
fig.set_size_inches(15, 10)
N = len(corr_mean_array)
axes[0][0].vlines(vlines, ymin=corr_y_min, ymax=corr_y_max, color='red', linestyle=linestyle)
axes[0][0].vlines(vlines_session, ymin=corr_y_min, ymax=corr_y_max, color='blue', linestyle=linestyle)
axes[0][0].plot(np.arange(1, N+1), corr_mean_array)
axes[0][0].legend(('TrialDays', 'Testing', 'Corr'))
# axes[0].set_xticks(np.arange(0,N)[::2])
# axes[0].set_xticklabels(trial_name_array[::2])
# axes[0].set_xlabel('trial')
axes[0][0].set_title('correlation')
axes[0][0].set_ylabel('mean')
axes[0][0].set_ylim(0.4, 0.7)


axes[1][0].vlines(vlines, ymin=pnr_y_min, ymax=pnr_y_max, color='red', linestyle=linestyle)
axes[1][0].vlines(vlines_session, ymin=pnr_y_min, ymax=pnr_y_max, color='blue', linestyle=linestyle)
axes[1][0].plot(np.arange(1, N+1), pnr_mean_array, c='orange')
axes[1][0].legend(('TrialDays', 'Testing', 'pnr'))
#axes[1].set_xticks(np.arange(0, N)[::2])
#axes[1].set_xticklabels(trial_name_array[::2])
axes[1][0].set_title('pnr')
axes[1][0].set_ylabel('mean')
axes[1][0].set_xlabel('trial')
axes[1][0].set_ylim(0, 10)

N = len(corr_mean_array_is_rest)
axes[0][1].plot(np.arange(1, N+1), corr_mean_array_is_rest)
axes[0][1].vlines(vlines, ymin=corr_y_min, ymax=corr_y_max, color='red', linestyle=linestyle)
axes[0][1].vlines(vlines_session, ymin=corr_y_min, ymax=corr_y_max, color='blue', linestyle=linestyle)
# axes[0].set_xticks(np.arange(0,N)[::2])
# axes[0].set_xticklabels(trial_name_array[::2])
# axes[0].set_xlabel('trial')
axes[0][1].set_title('correlation_R')
axes[0][1].set_ylabel('mean')
axes[0][1].set_ylim(0.4, 0.7)


#axes[1].vlines(vlines, ymin=4.3, ymax=5.5, color='red', linestyle=linestyle)
axes[1][1].plot(np.arange(1, N+1), pnr_mean_array_is_rest, c='orange')
#axes[1].set_xticks(np.arange(0, N)[::2])
#axes[1].set_xticklabels(trial_name_array[::2])
axes[1][1].vlines(vlines, ymin=pnr_y_min, ymax=pnr_y_max, color='red', linestyle=linestyle)
axes[1][1].vlines(vlines_session, ymin=pnr_y_min, ymax=pnr_y_max, color='blue', linestyle=linestyle)
axes[1][1].set_title('pnr_is_rest')
axes[1][1].set_ylabel('mean')
axes[1][1].set_xlabel('trial')
axes[1][1].set_ylim(1, 10)


#axes[1].set_ylim(4.3, 8.2)
plt.subplots_adjust()
fig.savefig('data/interim/source_extraction/trial_wise/meta/figures/fig:corrpnrphotobleaching'+str(56165)+'_mean.png')



#%% Plot number of detected cells and number of accepted cells using diferent criteria for acceptance
   
pcc_iteration = [0.95,0.99]
min_SNR_iteration = [2,3,4,5]         # adaptive way to set threshold on the transient size
N_trials = 25

number_cells = np.zeros((len(pcc_iteration),len(min_SNR_iteration),N_trials))   ## matrix for saving number of detected components
number_cells_ac = np.zeros(number_cells.shape)  ## matrix for saving number of accepted components

number_cells_R = np.zeros(number_cells.shape)   ## matrix for saving number of detected components
number_cells_ac_R =np.zeros(number_cells.shape)   ## matrix for saving number of accepted components

i=0
for r_values_min in pcc_iteration:
    j=0
    for min_SNR in min_SNR_iteration:
        for trial in range(15,25):
            row = selected_rows.iloc[2*trial]
            # Get the index from the row
            index = row.name
            
            parameters_component_evaluation = {'min_SNR': min_SNR,
                                               'rval_thr': r_values_min,
                                               'use_cnn': False}
            main_component_evaluation(index,row,parameters_component_evaluation)
            component_evaluation_output = eval(row.loc['component_evaluation_output'])
            input_hdf5_file_path = component_evaluation_output['main']
    
            cnm = load_CNMF(input_hdf5_file_path)
            number_cells[i][j][trial] = len(cnm.estimates.C)
            number_cells_ac[i][j][trial] = len(cnm.estimates.idx_components)
        
            row = selected_rows.iloc[2*trial+1]
            # Get the index from the row
            index = row.name
            main_component_evaluation(index,row,parameters_component_evaluation)
            component_evaluation_output = eval(row.loc['component_evaluation_output'])
            input_hdf5_file_path = component_evaluation_output['main']
            
            cnm = load_CNMF(input_hdf5_file_path)
            number_cells_R[i][j][trial] = len(cnm.estimates.C)
            number_cells_ac_R[i][j][trial] = len(cnm.estimates.idx_components)
        j=j+1
    i=i+1

#%% Ploting    
N_trials=N_trials+1
vlines = [1,6,11,16,22,27]
vlines_session = [21]
ymin=5

fig, axes = plt.subplots(2,4, sharex=True)
fig.set_size_inches(12, 10)
linestyle = '-'
axes[0][0].plot(np.arange(1, N_trials), number_cells[0][0][:],linestyle=linestyle)
linestyle = ':'
axes[0][0].plot(np.arange(1, N_trials), number_cells_ac[0][0][:].T,linestyle=linestyle)
axes[0][0].plot(np.arange(1, N_trials), number_cells_ac[1][0][:].T,linestyle=linestyle)
axes[0][0].vlines(vlines, ymin=ymin, ymax=300, color='red', linestyle=linestyle)
axes[0][0].vlines(vlines_session, ymin=ymin, ymax=300, color='blue', linestyle=linestyle)
axes[0][0].set_title('min_SNR = 2')
axes[0][0].set_ylabel('#cells')
axes[0][0].set_xlabel('trial')
axes[0][0].legend(('DetectedCells', 'pcc=0.95', 'pcc=0.99'))
axes[0][0].set_ylim(ymin, 300)


axes[0][1].vlines(vlines, ymin=ymin, ymax=300, color='red', linestyle=linestyle)
axes[0][1].vlines(vlines_session, ymin=ymin, ymax=300, color='blue', linestyle=linestyle)
linestyle = '-'
axes[0][1].plot(np.arange(1, N_trials), number_cells[0][1][:],linestyle=linestyle)
linestyle = ':'
axes[0][1].plot(np.arange(1, N_trials), number_cells_ac[0][1][:].T,linestyle=linestyle)
axes[0][1].plot(np.arange(1, N_trials), number_cells_ac[1][1][:].T,linestyle=linestyle)
axes[0][1].set_title('min_SNR = 3')
axes[0][1].set_ylabel('#cells')
axes[0][1].set_xlabel('trial')
axes[0][1].set_ylim(ymin, 300)

axes[0][2].vlines(vlines, ymin=ymin, ymax=300, color='red', linestyle=linestyle)
axes[0][2].vlines(vlines_session, ymin=ymin, ymax=300, color='blue', linestyle=linestyle)
linestyle = '-'
axes[0][2].plot(np.arange(1, N_trials), number_cells[0][2][:],linestyle=linestyle)
linestyle = ':'
axes[0][2].plot(np.arange(1, N_trials), number_cells_ac[0][2][:].T,linestyle=linestyle)
axes[0][2].plot(np.arange(1, N_trials), number_cells_ac[1][2][:].T,linestyle=linestyle)
axes[0][2].set_title('min_SNR = 4')
axes[0][2].set_ylabel('#cells')
axes[0][2].set_xlabel('trial')    
axes[0][2].set_ylim(ymin, 300)


axes[0][3].vlines(vlines, ymin=ymin, ymax=300, color='red', linestyle=linestyle)
axes[0][3].vlines(vlines_session, ymin=ymin, ymax=300, color='blue', linestyle=linestyle)
linestyle = '-'
axes[0][3].plot(np.arange(1, N_trials), number_cells[0][3][:],linestyle=linestyle)
linestyle = ':'
axes[0][3].plot(np.arange(1, N_trials), number_cells_ac[0][3][:].T,linestyle=linestyle)
axes[0][3].plot(np.arange(1, N_trials), number_cells_ac[1][3][:].T,linestyle=linestyle)
axes[0][3].set_title('min_SNR = 5')
axes[0][3].set_ylabel('#cells')
axes[0][3].set_xlabel('trial')
axes[0][3].set_ylim(ymin, 300)


#fig, axes = plt.subplots(2,2, sharex=True)
#fig.set_size_inches(9, 7)
axes[1][0].vlines(vlines, ymin=ymin, ymax=60, color='red', linestyle=linestyle)
axes[1][0].vlines(vlines_session, ymin=ymin, ymax=60, color='blue', linestyle=linestyle)
linestyle = '-'
axes[1][0].plot(np.arange(1, N_trials), number_cells_R[0][0][:],linestyle=linestyle)
linestyle = ':'
axes[1][0].plot(np.arange(1, N_trials), number_cells_ac_R[0][0][:].T,linestyle=linestyle)
axes[1][0].plot(np.arange(1, N_trials), number_cells_ac_R[1][0][:].T,linestyle=linestyle)
axes[1][0].set_title('min_SNR = 2_Resting')
axes[1][0].set_ylabel('#cells')
axes[1][0].set_xlabel('trial')
axes[1][0].set_ylim(ymin, 60)


axes[1][1].vlines(vlines, ymin=ymin, ymax=60, color='red', linestyle=linestyle)
axes[1][1].vlines(vlines_session, ymin=ymin, ymax=60, color='blue', linestyle=linestyle)
linestyle = '-'
axes[1][1].plot(np.arange(1, N_trials), number_cells_R[0][1][:],linestyle=linestyle)
linestyle = ':'
axes[1][1].plot(np.arange(1, N_trials), number_cells_ac_R[0][1][:].T,linestyle=linestyle)
axes[1][1].plot(np.arange(1, N_trials), number_cells_ac_R[1][1][:].T,linestyle=linestyle)
axes[1][1].set_title('min_SNR = 3_Resting')
axes[1][1].set_ylabel('#cells')
axes[1][1].set_xlabel('trial')
axes[1][1].set_ylim(ymin, 60)

axes[1][2].vlines(vlines, ymin=ymin, ymax=60, color='red', linestyle=linestyle)
axes[1][2].vlines(vlines_session, ymin=ymin, ymax=60, color='blue', linestyle=linestyle)
linestyle = '-'
axes[1][2].plot(np.arange(1, N_trials), number_cells_R[0][2][:],linestyle=linestyle)
linestyle = ':'
axes[1][2].plot(np.arange(1, N_trials), number_cells_ac_R[0][2][:].T,linestyle=linestyle)
axes[1][2].plot(np.arange(1, N_trials), number_cells_ac_R[1][2][:].T,linestyle=linestyle)
axes[1][2].set_title('min_SNR = 4_Resting')
axes[1][2].set_ylabel('#cells')
axes[1][2].set_xlabel('trial')    
axes[1][2].set_ylim(ymin, 60)

axes[1][3].vlines(vlines, ymin=ymin, ymax=60, color='red', linestyle=linestyle)
axes[1][3].vlines(vlines_session, ymin=ymin, ymax=60, color='blue', linestyle=linestyle)
linestyle = '-'
axes[1][3].plot(np.arange(1, N_trials), number_cells_R[0][3][:],linestyle=linestyle)
linestyle = ':'
axes[1][3].plot(np.arange(1, N_trials), number_cells_ac_R[0][3][:].T,linestyle=linestyle)
axes[1][3].plot(np.arange(1, N_trials), number_cells_ac_R[1][3][:].T,linestyle=linestyle)
axes[1][3].set_title('min_SNR = 5_Resting')
axes[1][3].set_ylabel('#cells')
axes[1][3].set_xlabel('trial')
axes[1][3].set_ylim(ymin, 60)

fig.savefig('data/interim/component_evaluation/trial_wise/meta/figures/fig:cell_selection_acceptance_all.png')

