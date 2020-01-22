# -*- coding: utf-8 -*-
"""
Created on November 2019

@author: Melisa
"""

import logging
import matplotlib.pyplot as plt
import caiman as cm

import datetime
import os
import numpy as np

import data_base_manipulation as db
import paths as paths
from skimage import io


def run_equalizer(selected_rows, states_df, parameters,session_wise = False):
    '''

    This function is meant to help with differences in contrast in different trials and session, to equalize general
    brightness or reduce photobleaching. It corrects the video and saves them in the corrected version. It can be run
    with the already aligned videos or trial by trial. for trial by trial, a template is required.

    params selected_rows: pd.DataFrame ->  A dataframe containing the analysis states you want to have equalized
    params states_df: pd.DataFrame -> A dataframe containing all the analysis data base
    params parameters: dict -> contains parameters concerning equalization

    returns : None
    '''

    # Sort the dataframe correctly
    df = selected_rows.sort_values(by=paths.multi_index_structure)
    # Determine the output path
    output_tif_file_path = f'data/interim/equalizer/main/'
    mouse, session, init_trial, *r = df.iloc[0].name

    histogram_name = f'mouse_{mouse}_session_{session}_init_trial_{init_trial}'
    output_steps_file_path = f'data/interim/equalizer/meta/figures/histograms/'+histogram_name

    try:
        df.reset_index()[['trial', 'is_rest']].set_index(['trial', 'is_rest'], verify_integrity=True)
    except ValueError:
        logging.error('You passed multiple of the same trial in the dataframe df')
        return df

    #creates an output dictionary for the data base
    output = {
        'main': {},
        'meta': {
            'analysis': {
                'analyst': os.environ['ANALYST'],
                'date': datetime.datetime.today().strftime("%m-%d-%Y"),
                'time': datetime.datetime.today().strftime("%H:%M:%S")
            },
            'duration': {}
        }
    }

    if session_wise: ## UNDER DEVELOPMENT
        row_local = df.iloc[0]
        input_tif_file_list =eval(row_local['alignment_output'])['main']
        movie_original = cm.load(input_tif_file_list)  # load video as 3d array already concatenated
        movie_equalized = np.empty_like(movie_original)
        source = movie_original[0:100, :, :]
        # equalize all the videos loads in m_list_reshape with the histogram of source
        for j in range(int(movie_original.shape[0] / 100)):
            want_to_equalize = movie_original[j * 100:(j + 1) * 100, :, :]
            movie_equalized[j * 100:(j + 1) * 100, :, :] = do_equalization(reference=want_to_equalize, source=source)
        # Save the movie
        index = row_local.name
        new_index = db.replace_at_index1(index, 4 + 3, 2)
        row_local.name = new_index

        output['main'] = output_tif_file_path + db.create_file_name(0,row_local.name) + '.mmap'
        auxiliar = eval(row_local.loc['alignment_output'])
        auxiliar.update({'equalizing_output' : output})
        row_local.loc['decoding_output'] = str(auxiliar)
        movie_equalized.save(output_tif_file_path + db.create_file_name(0,row_local.name) + '.mmap')
        states_df = db.append_to_or_merge_with_states_df(states_df, row_local)


    else:
        # Get necessary parameters and create a list with the paths to the relevant files
        decoding_output_list = []
        input_tif_file_list = []
        trial_index_list = []
        for idx, row in df.iterrows():
            decoding_output = eval(row.loc['decoding_output'])
            decoding_output_list.append(decoding_output)
            input_tif_file_list.append(decoding_output['main'])
            trial_index_list.append(db.get_trial_name(idx[2], idx[3]))

        # this was something for ploting while testing, can be removed
        #colors = []
        #for i in range(len(df)):
        #    colors.append('#%06X' % randint(0, 0xFFFFFF))

        #load the videos as np.array to be able to manipulate them
        m_list = []
        legend = []
        shape_list = []
        h_step = parameters['histogram_step']
        for i in range(len(input_tif_file_list)):
            im = io.imread(input_tif_file_list[i]) #load video as 3d array
            m_list.append(im)                      # and adds all the videos to a list
            shape_list.append(im.shape)            # list of sizes to cut the videos in time for making all of them having the same length
            #legend.append('trial = ' + f'{df.iloc[i].name[2]}')

        min_shape = min(shape_list)
        new_shape = (100 * int(min_shape[0]/100),min_shape[1],min_shape[2]) # new videos shape
        m_list_reshape=[]
        m_list_equalized = []
        source =m_list[0][0:100,:,:]
        #equalize all the videos loades in m_list_reshape with the histogram of source

        for i in range(len(input_tif_file_list)):
            video= m_list[i]
            m_list_reshape.append(video[:new_shape[0],:,:])
            equalized_video = np.empty_like(video[:new_shape[0],:,:])
            for j in range(int(min_shape[0]/100)):
                want_to_equalize = m_list_reshape[i][j*100:(j+1)*100,:,:]
                equalized_video[j*100:(j+1)*100,:,:] = do_equalization(reference=want_to_equalize,  source=source)
            m_list_equalized.append(equalized_video)

    #convert the 3d np.array to a caiman movie and save it as a tif file, so it can be read by motion correction script.
    for i in range(len(input_tif_file_list)):
        # Save the movie
        row_local = df.iloc[i]
        movie_original = cm.movie(m_list_reshape[i])
        movie_equalized = cm.movie(m_list_equalized[i])
        # Write necessary variables to the trial index and row_local
        index = row_local.name
        new_index = db.replace_at_index1(index, 4 + 0, 2)
        row_local.name = new_index
        output['main'] = output_tif_file_path + db.create_file_name(0,row_local.name) + '.tif'
        auxiliar = eval(row_local.loc['decoding_output'])
        auxiliar.update({'equalizing_output' : output})
        row_local.loc['decoding_output'] = str(auxiliar)
        movie_equalized.save(output_tif_file_path + db.create_file_name(0,row_local.name) + '.tif')
        states_df = db.append_to_or_merge_with_states_df(states_df, row_local)

    db.save_analysis_states_database(states_df, paths.analysis_states_database_path, paths.backup_path)

    #ALL OF THIS IS FOR PLOTTING AND SHOULD BE MOVED AND CREATE A FUNCTION IN FIGURES FOR PLOTTING THIS THINGS. (LATER)
    #aligned_video_original = np.zeros((new_shape[0]*5,5))
    #aligned_video = np.zeros((new_shape[0]*5,5))
    #for i in range(len(input_tif_file_list)):
     #   aligned_video_original[i*new_shape[0]:(i+1)*new_shape[0],1] = m_list_reshape[i][:,600,500]
      #  aligned_video[i*new_shape[0]:(i+1)*new_shape[0],1] = m_list_equalized[i][:,600,500]

    #figure, axes = plt.subplots(1)
    #axes.plot(np.linspace(0, len(aligned_video_original), len(aligned_video_original)), aligned_video_original[:, 1])
    #axes.plot(np.linspace(0, len(aligned_video_original), len(aligned_video_original)), aligned_video[:, 1])
    #axes.set_xlabel('Frames')
    #axes.set_ylabel('Pixel value (gray scale)')
    #axes.legend(['Original aligned signal', 'Histogram matching aligned signal'])
    #figure.savefig('Example_histogram_matching_3')

    #m_list_equalized = do_equalization(source=m_list_reshape[0][0:100,:,:], reference=m_list_reshape[i][0:100,:,:])

    #hist_template_video, bins_template = np.histogram(m_list_reshape[0][0:100,:,:].flatten(),bins=np.linspace(0,2**10), density= True)
    #hist_source_video, bins_source = np.histogram(m_list_reshape[i][0:100,:,:].flatten(),bins = np.linspace(0,2**10),density=True)
    #hist_equalized_video, bins_equalized = np.histogram(m_list_equalized[i][0:100,:,:].flatten(),bins = np.linspace(0,2**10),density=True)

    #figure, axes = plt.subplots(2,2)
    #axes[0,0].imshow(m_list[0][0,:,:], cmap = 'gray')
    #axes[1,0].imshow(m_list[i][0,:,:], cmap = 'gray')
    #axes[1,1].imshow(m_list_equalized[0,:,:], 'gray')
    #axes[0,1].plot(bins_template[:-1],hist_template_video, color = 'r')
    #axes[0,1].plot(bins_source[:-1],hist_source_video,'--', color = 'b')
    #axes[0,1].plot(bins_equalized[:-1],hist_equalized_video, '*', color = 'g')
    #axes[0,1].legend(['Template','Source','Equalized_Video'])
    #axes[0,1].set_xlabel('Pixel Intensity (gray scale)')
    #axes[0,1].set_ylabel('Density')
    #axes[0, 0].set_title('Template')
    #axes[1, 0].set_title('Source')
    #axes[1, 1].set_title('Equalized')

    return

def do_global_equalization(source=None):

    # flatten(turns an n-dim array into
    src=source.flatten()

    # sorted pixel values
    srcS= np.argsort(src)

    # array for the equalization




def do_equalization(source = None, reference = None):

    '''
    Created on Fri May 19 22:34:51 2017

    @author: sebalander (Sebastian Arroyo, Universidad de Quilmes, Argentina)

    do_equalization(source, reference) -> using 'cumulative density'
    Takes an image source and reorder the pixel values to have the same
    pixel distribution as reference.

    params : source -> original image which distribution is taken from
    params: reference -> image which pixel values histograms is wanted to be changed

    return: new source image that has the same pixel values distribution as source.
    '''

    # flatten (turns an n-dim-array into 1-dim)
    srcV = source.flatten()
    refV = reference.flatten()

    # sorted pixel values
    srcInd = np.argsort(srcV)
    #srcSort = np.sort(srcV)
    refInd = np.argsort(refV)

    #assign...
    dst = np.empty_like(refV)
    dst[refInd] = srcV[srcInd]
    #dst[refInd] = srcSort

    dst.shape = reference.shape

    return dst

'''
#%%%b gitignore

figure, axes = plt.subplots(3,2)
axes[0,0].imshow(movie_original[0,:,:], cmap = 'gray')
axes[0,0].set_title('ROI')


[x_, _x, y_, _y] = [15,25,15,25]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='r', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)
axes[0,1].hist(movie_original[:,20,20],20, color = 'r')
axes[0,1].set_xlim((700,1000))
axes[0,1].set_ylabel('#')
axes[0,1].set_xlabel('Pixel value')

[x_, _x, y_, _y] = [15,25,135,145]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='b', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)
axes[1,0].hist(movie_original[:,20,140],20, color = 'b')
axes[1,0].set_xlim((700,1000))
axes[1,0].set_ylabel('#')
axes[1,0].set_xlabel('Pixel value')

[x_, _x, y_, _y] = [135,145,135,145]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='g', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)
axes[1,1].hist(movie_original[:,140,140],20, color = 'g')
axes[1,1].set_xlim((700,1000))
axes[1,1].set_ylabel('#')
axes[1,1].set_xlabel('Pixel value')

[x_, _x, y_, _y] = [85,95,25,35]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='m', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)
axes[2,0].hist(movie_original[:,90,30],20, color = 'm')
axes[2,0].set_xlim((700,1000))
axes[2,0].set_ylabel('#')
axes[2,0].set_xlabel('Pixel value')

[x_, _x, y_, _y] = [25,35,85,95]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='c', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)
axes[2,1].hist(movie_original[:,30,90],20, color = 'c')
axes[2,1].set_xlim((700,1000))
axes[2,1].set_ylabel('#')
axes[2,1].set_xlabel('Pixel value')


#%% also gitignore


figure, axes = plt.subplots(3,2)
axes[0,0].imshow(movie_original[0,:,:], cmap = 'gray')
axes[0,0].set_title('ROI')

[x_, _x, y_, _y] = [15,25,15,25]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='r', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)

for i in range(len(m_list)):
    axes[0,1].hist(m_list[i][:,20,20],bins = np.arange(600,1000))
axes[0,1].set_xlim((500,1000))
axes[0,1].set_ylabel('#')
axes[0,1].set_xlabel('Pixel value')
axes[0,1].set_title('RED SQUARE')
axes[0,1].legend(['1','2','3','4','5'])

[x_, _x, y_, _y] = [15,25,135,145]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='b', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)

for i in range(len(m_list)):
    axes[1,0].hist(m_list[i][:,20,140],bins = np.arange(600,1000))
axes[1,0].set_xlim((500,1000))
axes[1,0].set_ylabel('#')
axes[1,0].set_xlabel('Pixel value')
axes[1,0].set_title('BLUE SQUARE')
axes[1,0].legend(['1','2','3','4','5'])



[x_, _x, y_, _y] = [135,145,135,145]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='g', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)
for i in range(len(m_list)):
    axes[1,1].hist(m_list[i][:,140,140],bins = np.arange(600,1000))
axes[1,1].set_xlim((500,1000))
axes[1,1].set_ylabel('#')
axes[1,1].set_xlabel('Pixel value')
axes[1,1].set_title('GREEN SQUARE')
axes[1,1].legend(['1','2','3','4','5'])

[x_, _x, y_, _y] = [85,95,25,35]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='m', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)
for i in range(len(m_list)):
    axes[2,0].hist(m_list[i][:,90,30],bins = np.arange(600,1000))
axes[2,0].set_xlim((500,1000))
axes[2,0].set_ylabel('#')
axes[2,0].set_xlabel('Pixel value')
axes[2,0].set_title('MAGENTA SQUARE')
axes[2,0].legend(['1','2','3','4','5'])


[x_, _x, y_, _y] = [25,35,85,95]
rect = Rectangle((y_, x_), _y - y_, _x - x_, fill=False, color='c', linestyle='-', linewidth=2)
axes[0, 0].add_patch(rect)
for i in range(len(m_list)):
    axes[2,1].hist(m_list[i][:,30,90],bins = np.arange(600,1000))
axes[2,1].set_xlim((500,1000))
axes[2,1].set_ylabel('#')
axes[2,1].set_xlabel('Pixel value')
axes[2,1].set_title('CYAN SQUARE')
axes[2,1].legend(['1','2','3','4','5'])
'''