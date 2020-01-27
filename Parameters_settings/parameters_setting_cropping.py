#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 09:19:20 2019

@author: Melisa, Morgane

This script is created for selection a cropping section from the videos and creates new files where only the region of
interest(ROI) is considered.

For testing different parameters in the upcoming parts of the pipeline, cropping parameters can be chosen to select
only a small region, in a way that this will accelerate the time requirements for running different tests.

Once the new cropping parameters are selected, the data base is update. If the cropping parameters are new and had never
been use for a particular mouse, session, trial, resting condition, a new line will be added to the data base and the
cropping version will be the previous maximum plus one. If the parameters where already used, the cropping version will not
be increased, but the cropping files will be rewritten.

Cropping parameters should be always the same for a mouse, so after selection the last part of this script can be use
to set the cropping parameters in the parameters data base for all the sessions and trials of a mouse.

"""


from Database.database_connection import database
from analysis.figures import plot_movie_frame, plot_movie_frame_cropped
from Steps.cropping import run_cropper
cursor = database.cursor()

#selection of data to crop. Take into account that cropping is more or less the same for every session in one mouse.
mouse = 32364
session = 1
trial = 10
is_rest = 1
# CROPPING

sql ="SELECT decoding_main FROM Analysis WHERE mouse=%s AND session= %s AND trial =%s AND is_rest=%s  "
val = [mouse, session, trial, is_rest]
cursor.execute(sql, val)
var = cursor.fetchone()

for x in var:
    mouse_row = x

#shows one frame of the movie so the cropping region can be choosen.
plot_movie_frame(mouse_row)

#manualy load the cropping region of interest

mouse_row = run_cropper(mouse_row)

plot_movie_frame_cropped(mouse_row)

