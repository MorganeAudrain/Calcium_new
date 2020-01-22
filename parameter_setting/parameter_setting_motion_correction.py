#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 09:19:20 2019

@author: Melisa,Morgane

This script is designed to test the impact of different motion correction parameters in the pre-processed images.

The two main parameters that are explored are:

    gSig - > size of the gaussian filter that is applied to the image before motion corrected.
    strides_vector ->

    All can be run in a pw_rigid / rigid mode.

gSig sizes are selected in a np.array, and it's values can be changed in line: gSig_filters = 2*np.arange(0,5)+3
The effect of this filters are first ploted using the function in src.analysis.figures.get_fig_gSig_filt_vals.

After running motion correction in all the selected gSig values, the data base is updates with the new versions of
motion correction. If the metrics are computed (using function  metrics.get_metrics_motion_correction) the data base is
also updated with the quality metrics of motion correction (in this case crispness of the summaty images of mean image
and correlation image).

After selection of a gSig value, strides can be testes as a relevant parameter, and the same data base and metrics
saving applies here.

At the end of the script all crispness can be compare. Take into account that crispness (as a Frobenious norm that is not
normalized now) is dependent on the size of the summary image, so only videos that have the same cropping size can be
compared.

Last part of the script is for setting in the parameters data base the selected values for this particular mouse, session,
trial and resting condition. After running a few conditions check whether the same can be used for all the mice.

"""

import sys
import psutil
import logging
import numpy as np


import configuration
import caiman as cm
from analysis.figures import get_fig_gSig_filt_vals

from steps.motion_correction import run_motion_correction as main_motion_correction
from steps.motion_correction import database
import analysis.metrics as metrics
import analysis.figures as figures

mycursor = database.cursor()

# Selected mouse
mouse = 32364
session = 1
trial = 10
is_rest = 1
cropping_version = 1

# Select the file that we want motion correct
sql ="SELECT cropping_main,id FROM Analysis WHERE mouse=%s AND session= %s AND trial =%s AND is_rest=%s AND cropping_v= %s "
val=[mouse,session,trial,is_rest,cropping_version]
mycursor.execute(sql,val)
myresult = mycursor.fetchall()
data=[]
for x in myresult:
    data += x
mouse_row = data[0]

gSig_filters = 2*np.arange(0,5)+3
get_fig_gSig_filt_vals(mouse_row,gSig_filters)


#start a cluster
n_processes = psutil.cpu_count()
cm.cluster.stop_server()
# Start a new cluster
c, dview, n_processes = cm.cluster.setup_cluster(backend='local',
                                                 n_processes=n_processes,  # number of process to use, if you go out of memory try to reduce this one
                                                single_thread=False)

logging.info(f'Starting cluster. n_processes = {n_processes}.')

# Run all the motion correction steps but changing the filter size parameter
gSig_v=0
for gSig in gSig_filters:
    print(gSig)
    sql = "INSERT INTO Parameters (motion_correct,pw_rigid,save_movie_rig,gSig_filt,max_shifts,niter_rig,strides,overlaps,upsample_factor_grid,num_frames_split,max_deviation_rigid,shifts_opencv,use_cuda,nonneg_movie,border_nan) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) WHERE decoding_v=%s AND cropping_v =%s AND id=%s AND gSig_v=%s"
    val = [True, True, False, (gSig, gSig), (25, 25), 1, (96, 96), (48, 48), 2, 80, 15, True, False, True, 'copy', 1,
           cropping_version, data[1],gSig_v]
    mycursor.execute(sql, val)
    database.commit()
    mouse_row_new=main_motion_correction(mouse_row,val,dview)
    gSig_v +=1
    # Compute metrics for quality assessment in motion corrected movies'crispness'
    mouse_row_new = metrics.get_metrics_motion_correction(mouse_row_new, crispness = True)

#%%
# Choose filter size=5
# Run all the motion correction steps but changing the strides size explore the same as in the paper
# (24/48), (48/48), (96,48) , (128,48)
# Select rows from the data base fo the next analysis step motion correction

strides_vector=[24,48,96,128]
strides_v=0
for strides in strides_vector:
    print(strides)
    sql = "INSERT INTO Parameters (motion_correct,pw_rigid,save_movie_rig,gSig_filt,max_shifts,niter_rig,strides,overlaps,upsample_factor_grid,num_frames_split,max_deviation_rigid,shifts_opencv,use_cuda,nonneg_movie,border_nan) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) WHERE decoding_v=%s AND cropping_v =%s AND id=%s AND strides_v=%s"
    val = [True, True, False, (5, 5), (25, 25), 1, (strides, strides), (48, 48), 2, 80, 15, True, False, True, 'copy', 1,
           cropping_version, data[1],strides_v]
    mycursor.execute(sql, val)
    database.commit()
    mouse_row_new=main_motion_correction(mouse_row,val,dview)
    # Compute metrics for quality assessment in motion corrected movies'crispness'
    mouse_row_new = metrics.get_metrics_motion_correction(mouse_row_new, crispness = True)
    states_df = db.append_to_or_merge_with_states_df(states_df, mouse_row_new)
    db.save_analysis_states_database(states_df, path=analysis_states_database_path, backup_path = backup_path)
    strides_v +=1

#save state version index to comparare in next step
index = mouse_row.name

#%%
# Now compare the result using crispness for the used analyzed parameters

#choose all states corresponding to this particular analysis state
# With the parameter max_version = False, all the analysis states with the same previous parameters that the current one
# are selected

selected_rows = db.select(states_df,'motion_correction',mouse = index[0], session = index[1],trial = index[2],
                          is_rest = index [3], decoding_v= index[4] , cropping_v = index[5],max_version=False)

#choose only the ones that explores filter size (let's think if this make sense...we can just select the best in all)

# Choose the best one using crispness measurement in summary image (mean or corr_image, both values are save)

#visualizarion
crispness_mean_original, crispness_corr_original, crispness_mean, crispness_corr = metrics.compare_crispness(
    selected_rows)
crispness_figure = figures.plot_crispness_for_parameters(selected_rows)
selected_version = np.argmin(crispness_mean)
selected_parameters = eval(selected_rows.iloc[selected_version]['motion_correction_parameters'])
print('Motion Correction selected parameters = ')
print(selected_parameters)



