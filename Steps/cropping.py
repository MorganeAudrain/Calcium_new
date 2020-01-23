# -*- coding: utf-8 -*-
"""
@author: Sebastian,Casper,Melisa,Morgane
"""

import caiman as cm
import logging
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


def run_cropper(input_path):
    '''
    This function takes in a decoded analysis state and crops it according to 
    specified cropping points.
    
    Args:
        input_path the path of the decoding file
            
    Returns
        row: pd.DataFrame object
            The row corresponding to the cropped analysis state. 
    '''

    # Determine output .tif file path
    sql="SELECT mouse,session,trial,is_rest,decoding_v,cropping_v FROM Analysis WHERE decoding_main=%s ORDER BY cropping_v"
    val=[input_path,]
    mycursor.execute(sql,val)
    myresult = mycursor.fetchall()
    data=[]
    for x in myresult:
        data += x

    file_name = f"mouse_{data[0]}_session_{data[1]}_trial_{data[2]}.{data[3]}.v{data[5]}.{data[4]}"
    output_tif_file_path = f"data/interim/cropping/main/{file_name}.tif"

    # update the database
    if data[4] == 0:
        data[4]=1
        sql1 = "UPDATE Analysis SET cropping_main=%s,cropping_v=%s WHERE decoding_main=%s "
        val1 = [output_tif_file_path,data[4],input_path]
        mycursor.execute(sql1,val1)
        database.commit()
    else:
        data[4] +=1
        sql2 = "INSERT INTO Analysis (cropping_main,cropping_v) VALUES (%s,%s)"
        val2 = [output_tif_file_path, data[4]]
        mycursor.execute(sql2, val2)
        database.commit()
        sql3="UPDATE Analysis SET decoding_main=%s,decoding_v=%s,mouse=%s,session=%s,trial=%s,is_rest=%s WHERE cropping_main=%s AND cropping_v=%s"
        val3=[input_path,data[5],data[0],data[1],data[2],data[3],output_tif_file_path,data[4]]
        mycursor.execute(sql3,val3)
        database.commit()
    # Spatial copping  
    logging.info('Loading movie')
    m = cm.load(input_path)
    logging.info('Loaded movie')

    # Choose crop parameters
    x1 = int(input("Limit X1 : "))
    x2 = int(input("Limit X2 : "))
    y1 = int(input("Limit Y1 : "))
    y2 = int(input("Limit Y2 : "))
    sql = "INSERT INTO Analysis (crop_spatial,cropping_points_spatial,crop_temporal,cropping_points_temporal) VALUES (%s,%s,%s,%s) WHERE cropping_main=%s AND cropping_v=%s"
    val = [True,[y1, y2, x1, x2],False,[],output_tif_file_path,data[4]]
    mycursor.execute(sql, val)
    database.commit()

    [x_,_x,y_,_y] = [y1, y2, x1, x2]

    logging.info('Performing spatial cropping')
    m = m[:,x_:_x,y_:_y]
    logging.info(' Spatial cropping finished')

    # Save the movie
    m.save(output_tif_file_path)

    return output_tif_file_path

