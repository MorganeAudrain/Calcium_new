#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 13 11:36 2019

@author: Morgane

Create a new database for Calcium imaging data in SQL

"""
import mysql.connector

# connection to SQL

database = mysql.connector.connect(
  host="localhost",
  user="root",
  passwd="M-A-so-1996",
    use_pure=True
)

print(database)
mycursor = database.cursor()

#%% Create the database

mycursor.execute("CREATE DATABASE Calcium_imaging")

#%% check if the database exist

mycursor.execute("SHOW DATABASES")

for x in mycursor:
  print(x)

