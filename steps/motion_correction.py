# -*- coding: utf-8 -*-
"""
@author: Sebastian,Casper
"""

import os
import logging
import datetime
import pickle
import numpy as np
import caiman as cm
from caiman.motion_correction import MotionCorrect, high_pass_filter_space
from caiman.source_extraction.cnmf import params as params
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


def run_motion_correction(cropped_file,parameters, dview):

    """

    This is the function for motion correction. Its goal is to take in a decoded and
    cropped .tif file, perform motion correction, and save the result as a .mmap file.

    This function is only runnable on the cn76 server because it requires parralel processing.

    Args:
        cropped_file
        parameters :  motion_correction_parameters
        dview: cluster

    Returns:
        row: pd.DataFrame object
            The row corresponding to the motion corrected analysis state.
    """

    # Forcing parameters
    if not parameters['pw_rigid']:
        parameters['save_movie_rig'] = True

    # Get output file paths
    sql="SELECT mouse,session,trial,is_rest,cropping_v,decoding_v,motion_correction_v FROM Analysis WHERE cropping_main=%s "
    val=[cropped_file,]
    mycursor.execute(sql,val)
    myresult = mycursor.fetchall()
    data=[]
    for x in myresult:
        data+=x

    file_name = f"mouse_{data[0]}_session_{data[1]}_trial_{data[2]}.{data[3]}.v{data[5]}.{data[4]}.{data[6]+1}"
    data_dir = 'data/interim/motion_correction/'
    output_meta_pkl_file_path = data_dir + f'meta/metrics/{file_name}.pkl'

    if data[6] == 0:
        sql1 = "UPDATE Analysis SET motion_correction_meta_metrics=%s, motion_correction_v=%s WHERE decoding_main=%s  "
        val1 = [output_meta_pkl_file_path, 1]
        mycursor.execute(sql1,val1)
        database.commit()
    else:
        sql2 = "INSERT INTO Analysis (motion_correction_meta_metrics,motion_correction_v) VALUES (%s,%s)"
        val2 = [output_meta_pkl_file_path, data[4]+1]
        mycursor.execute(sql2, val2)
        database.commit()

    # Calculate movie minimum to subtract from movie 
    min_mov = np.min(cm.load(cropped_file))
    # Apply the parameters to the CaImAn algorithm
    caiman_parameters = parameters
    caiman_parameters['min_mov'] = min_mov
    opts = params.CNMFParams(params_dict = caiman_parameters)

    # Rigid motion correction (in both cases)
    logging.info(f' Performing rigid motion correction')
    t0 = datetime.datetime.today()

    
    # Create a MotionCorrect object   
    mc = MotionCorrect([cropped_file], dview = dview, **opts.get_group('motion'))
    # Perform rigid motion correction
    mc.motion_correct_rigid(save_movie = parameters['save_movie_rig'], template = None)
    dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
    logging.info(f' Rigid motion correction finished. dt = {dt} min')
    # Obtain template, rigid shifts and border pixels
    total_template_rig = mc.total_template_rig
    shifts_rig = mc.shifts_rig 
    # Save template, rigid shifts and border pixels in a dictionary 
    meta_pkl_dict = {
            'rigid': {
                    'template': total_template_rig,
                    'shifts': shifts_rig,
                        }
            }
    output['meta']['duration'] = {'rigid': dt}
    output['meta']['cropping_points'] = [0,0,0,0]

    if parameters['save_movie_rig']:
        # Load the movie saved by CaImAn, which is in the wrong
        # directory and is not yet cropped
        logging.info(f'{index} Loading rigid movie for cropping')
        m_rig = cm.load(mc.fname_tot_rig[0])
        logging.info(f'{index} Loaded rigid movie for cropping')
        # Get the cropping points determined by the maximal rigid shifts
        x_, _x, y_, _y = get_crop_from_rigid_shifts(shifts_rig)
        # Crop the movie
        logging.info(f'{index} Cropping and saving rigid movie with cropping points: [x_, _x, y_, _y] = {[x_, _x, y_, _y]}')
        #m_rig = m_rig.crop(x_, _x, y_, _y, 0, 0)
        meta_pkl_dict['rigid']['cropping_points'] = [x_, _x, y_, _y]
        output['meta']['cropping_points'] = [x_, _x, y_, _y]
        # Save the movie 
        rig_role = 'alternate' if parameters['pw_rigid'] else 'main'
        fname_tot_rig  = m_rig.save(data_dir + rig_role + '/' + file_name + '_rig' + '.mmap',  order='C')         
        logging.info(f'{index} Cropped and saved rigid movie as {fname_tot_rig}')
        # Store the total path in output
        output[rig_role] = fname_tot_rig
        # Remove the remaining non-cropped movie
        os.remove(mc.fname_tot_rig[0])
            

    # If specified in the parameters, apply piecewise-rigid motion correction
    if parameters['pw_rigid']:
        logging.info(f'{index} Performing piecewise-rigid motion correction')
        t0 = datetime.datetime.today()
        # Perform non-rigid (piecewise rigid) motion correction. Use the rigid result as a template.
        mc.motion_correct_pwrigid(save_movie=True, template = total_template_rig)
        # Obtain template and filename
        total_template_els = mc.total_template_els
        fname_tot_els = mc.fname_tot_els[0]
        
        dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
        meta_pkl_dict['pw_rigid'] = {
                'template': total_template_els,
                'x_shifts': mc.x_shifts_els,
                'y_shifts': mc.y_shifts_els # removed them initially because they take up space probably
                }
        output['meta']['duration']['pw_rigid'] = dt
        logging.info(f'{index} Piecewise-rigid motion correction finished. dt = {dt} min')
    
        
        # Load the movie saved by CaImAn, which is in the wrong
        # directory and is not yet cropped
        logging.info(f'{index} Loading pw-rigid movie for cropping')
        m_els = cm.load(fname_tot_els)
        logging.info(f'{index} Loaded pw-rigid movie for cropping')
        # Get the cropping points determined by the maximal rigid shifts
        x_, _x, y_, _y = get_crop_from_pw_rigid_shifts(np.array(mc.x_shifts_els), 
                                                       np.array(mc.y_shifts_els))       
        # Crop the movie
        logging.info(f'{index} Cropping and saving pw-rigid movie with cropping points: [x_, _x, y_, _y] = {[x_, _x, y_, _y]}')
        #m_els = m_els.crop(x_, _x, y_, _y, 0, 0)
        meta_pkl_dict['pw_rigid']['cropping_points'] = [x_, _x, y_, _y]
        output['meta']['cropping_points'] = [x_, _x, y_, _y]
        # Save the movie 
        fname_tot_els  = m_els.save(data_dir + 'main/' + file_name + '_els' + '.mmap',  order='C')
        logging.info(f'{index} Cropped and saved rigid movie as {fname_tot_els}')

        # Remove the remaining non-cropped movie
        os.remove(mc.fname_tot_els[0])
                
        # Store the total path in output
        output['main'] = fname_tot_els
        output['meta']['cropping_points'] = [x_, _x, y_, _y]

    # Write meta results dictionary to the pkl file 
    pkl_file = open(output_meta_pkl_file_path, 'wb')
    pickle.dump(meta_pkl_dict, pkl_file)
    pkl_file.close()    

    # Write necessary variables to the trial index and row
    row_local.loc['motion_correction_output'] = str(output)
    row_local.loc['motion_correction_parameters'] = str(parameters)

    return row_local


def get_crop_from_rigid_shifts(shifts_rig):
    x_ = int(round(abs(np.array(shifts_rig)[:, 1].max()) if np.array(shifts_rig)[:, 1].max() > 0 else 0))
    _x = int(round(abs(np.array(shifts_rig)[:, 1].min()) if np.array(shifts_rig)[:, 1].min() < 0 else 0))
    y_ = int(round(abs(np.array(shifts_rig)[:, 0].max()) if np.array(shifts_rig)[:, 0].max() > 0 else 0))
    _y = int(round(abs(np.array(shifts_rig)[:, 0].min()) if np.array(shifts_rig)[:, 0].min() < 0 else 0))
    return x_, _x, y_, _y


def get_crop_from_pw_rigid_shifts(x_shifts_els, y_shifts_els):
    x_ = int(round(abs(x_shifts_els.max()) if x_shifts_els.max() > 0 else 0))
    _x = int(round(abs(x_shifts_els.min()) if x_shifts_els.min() < 0 else 0))
    y_ = int(round(abs(y_shifts_els.max()) if y_shifts_els.max() > 0 else 0))
    _y = int(round(abs(x_shifts_els.min()) if x_shifts_els.min() < 0 else 0))
    return x_, _x, y_, _y
