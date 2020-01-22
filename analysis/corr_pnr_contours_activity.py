#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  7 15:00:09 2019

@author: sebastian
"""

import os
import sys
import numpy as np
import configuration
import mysql.connector
import getpass

database = mysql.connector.connect(
  host="131.174.140.253",
  user="morgane",
  passwd=getpass.getpass(),
    database="Calcium_imaging",
    use_pure=True
)

mycursor = database.cursor()


import matplotlib.pyplot as plt

#%%
#Caiman importation
import caiman as cm
from caiman.utils.visualization import inspect_correlation_pnr
import caiman.source_extraction.cnmf as cnmf
import caiman.base.rois
from caiman.source_extraction.cnmf.cnmf import load_CNMF

from steps.component_evaluation import main as main_component_evaluation
from steps.source_extraction import get_fig_C_stacked as get_fig_C_stacked

#%%


## Open thw data base with all data
states_df = db.open_analysis_states_database()
## Select all the data corresponding to a particular mouse. Ex: 56165

selected_rows = db.select('decoding',56165)
sql ="SELECT decoding_main FROM Analysis WHERE mouse=%s "
val=[mouse,session,trial,is_rest]
mycursor.execute(sql,val)
myresult = mycursor.fetchone()

## plot countours


for i in range(0,15):
    
    row = selected_rows.iloc[i]
    # Get the index from the row
    index = row.name
    source_extraction_output = eval(row.loc['source_extraction_output'])
    corr_path, pnr_path = source_extraction_output['meta']['corr']['main'], source_extraction_output['meta']['pnr']['main']
    source_extraction_parameters = db.get_parameters('source_extraction', index[0], index[1], index[2], index[3], download_ = False)
    cn_filter = np.load(db.get_file(corr_path))
    pnr = np.load(db.get_file(pnr_path))
    
    fig = plt.figure(figsize = (15,10))
    min_corr_init = round(source_extraction_parameters['min_corr'],2)
    max_corr_init = round(cn_filter.max(),2)
    min_pnr_init = round(source_extraction_parameters['min_pnr'],1)
    max_pnr_init = 20


    # continuous
    cmap = 'viridis'
    cont_height = 0.5
    axes = np.empty((1,5), dtype = 'object')
    axes[0,0] = plt.axes([0.07,cont_height,0.2,0.4])
    im_corr_cont = axes[0,0].imshow(np.clip(cn_filter, min_corr_init, max_corr_init), cmap = cmap)
    axes[0,0].set_title('correlation')
    axes[0,1] = plt.axes([0.30, cont_height + 0.025, 0.01, 0.35])
    plt.colorbar(im_corr_cont, cax = axes[0,1])
    axes[0,2] = plt.axes([0.40,cont_height,0.2,0.4])
    im_pnr_cont = axes[0,2].imshow(np.clip(pnr, min_pnr_init, max_pnr_init), cmap = cmap)
    axes[0,2].set_title('pnr')
    axes[0,3] = plt.axes([0.63, cont_height + 0.025, 0.01, 0.35])
    plt.colorbar(im_pnr_cont, cax = axes[0,3])
    
    corr_pnr_plot_path='data/interim/source_extraction/trial_wise/meta/figures/corr_pnr/'+ db.create_file_name(4,index)+'.png'
    fig.savefig(corr_pnr_plot_path)
    
    
    cnm_file_path = source_extraction_output['main']
    cnm = load_CNMF(db.get_file(cnm_file_path))
    fig2=cnm.estimates.plot_contours(img=cn_filter, idx=cnm.estimates.idx_components)
    cnm_contours_plot_path='data/interim/source_extraction/trial_wise/meta/figures/corr_pnr/'+ db.create_file_name(4,index)+'_contours.png'
    fig2.savefig(corr_pnr_plot_path)
    
    idx_array = np.arange(cnm.estimates.C.shape[0])
    #plot components (non deconvolved)
    fig3=get_fig_C_stacked(cnm.estimates.C, idx_components = idx_array)
    cnm_activity_plot_path='data/interim/source_extraction/trial_wise/meta/figures/corr_pnr/'+ db.create_file_name(4,index)+'_activity.png'
    fig3.savefig(cnm_activity_plot_path)
    
