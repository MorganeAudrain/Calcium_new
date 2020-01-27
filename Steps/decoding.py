# -*- coding: utf-8 -*-
"""
@author: Sebastian,Casper,Morgane
"""


import os
import subprocess
import configuration
from Database.database_connection import database
mycursor = database.cursor()




def run_decoder(mouse, session,trial, is_rest):

    """

    This is the function for the decoding step. In the decoding step
    files are converted from .raw files to .tif files.

    This function is only usable on the Sebastian's account on the pastiera pc.

    Args:
        mouse, session, trial, is_rest: parameters of interest
    Returns:
        path of the decoded file

    """

    sql = "SELECT input, home_path FROM Analysis WHERE mouse = %s AND session = %s AND trial = %s AND is_rest = %s"
    val = (mouse, session, trial, is_rest)
    mycursor.execute(sql, val)
    result = mycursor.fetchall()

    input_raw_file = []
    for row in result:
        input_raw_file += row

    input_raw_file_paths = input_raw_file[1]+input_raw_file[0]+'.raw'

    #create the correct name for the file
    file_name = f"mouse_{mouse}_session_{session}_trial_{trial}_{is_rest}"
    output_tif_file_path = f"data/interim/decoding/main/{file_name}.tif"

    # Decoder paths
    py_inscopix = '/home/morgane/anaconda3/envs/inscopix_reader/bin/python'
    decoder = "/home/morgane/src/inscopix_reader_linux/python/downsampler.py"
            
    # Decoding
    print('Performing decoding on raw file')
    

    # Convert the output tif file path to the full path such that the downsampler.py script can use them.
    output_tif_file_path_full = os.path.join(os.environ['PROJECT_DIR'], output_tif_file_path)

    # Make a command usable by the decoder script (downsampler.py, see the script for more info)

    input_xml_file_path = input_raw_file[1] + input_raw_file[0] + '.xml'

    cmd = ' '.join([py_inscopix, decoder, '"' + input_raw_file_paths + '"', output_tif_file_path_full, '"' + input_xml_file_path + '"'])

    # Run the command
    subprocess.check_output(cmd, shell = True)

    print('Decoding finished')

    sql1 = "UPDATE Analysis SET decoding_v = %s, decoding_main= %s WHERE mouse = %s AND session = %s AND trial = %s AND is_rest = %s"
    val1 = (1, output_tif_file_path, mouse, session, trial, is_rest)
    mycursor.execute(sql1, val1)

    return output_tif_file_path

