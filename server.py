#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 12 11:02:57 2019

@author: melisa/casper/sebastian


In this file you will find function that connect the client to the server automatically

These were created by sebastian and casper

"""
import os
import logging
import configuration
if eval(os.environ['LOCAL']): 
    import paramiko

def get_SSH_connection():
    '''
    This function creates an ssh connection with the cluster using 
    paramiko and returns it. 
    '''
    server = os.environ['SERVER_HOSTNAME']
    username = os.environ['SERVER_USER']
    print(username)
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.connect(server, username=username)
    return ssh 


def download(path):
    ''' 
    This function downloads a file from the cn43 server onto the local machine.
    
    Args:
        path: str
            The path of the file relative to the project directory
    '''
    logging.info(f'Downloading {path} from server')
    ssh = get_SSH_connection()
    sftp = ssh.open_sftp()
    sftp.get(os.environ['PROJECT_DIR_SERVER'] + path, os.environ['PROJECT_DIR_LOCAL'] + path)
    sftp.close()
    ssh.close()
    logging.info('Downloading finished')


def upload(path):
    ''' 
    This function upload a file from the cn43 server onto the local machine.
    
    Args:
        path: str
            The path of the file relative to the project directory
    '''
    logging.info(f'Uploading {path} to server')
    ssh = get_SSH_connection()
    sftp = ssh.open_sftp()
    sftp.put(os.environ['PROJECT_DIR_LOCAL'] + path, os.environ['PROJECT_DIR_SERVER'] + path)
    sftp.close()
    ssh.close()
    logging.info('Uploading finished')