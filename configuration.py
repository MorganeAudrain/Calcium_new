import os

#%% ENVIRONMENT VARIABLES
os.environ['PROJECT_DIR_LOCAL'] = '/home/morgane/Calcium_imaging-master'
os.environ['PROJECT_DIR_SERVER'] = 'Calcium_imaging/'
os.environ['DATA_DIR_LOCAL'] = '/home/morgane/Calcium_imaging-master'

os.environ['DATA_DIR_SERVER'] ='data'

os.environ['CAIMAN_ENV_SERVER'] = '/memdyn/maudrain/caiman/bin/python'

ana_3 = "~/anaconda3"
inscopix_env = 'inscopix_reader'
os.environ['INSCOPIX_READER_LOCAL'] = os.path.join(ana_3, 'envs', inscopix_env, 'bin/python')
os.environ['INSCOPIX_READER_SERVER'] = "~/envs/inscopix_reader/bin/pyhton"

os.environ['LOCAL_USER'] = 'morgane'
os.environ['SERVER_USER'] = 'maudrain'
os.environ['SERVER_HOSTNAME'] = 'cn43'
os.environ['ANALYST'] = 'Morgane'

#%% PROCESSING
os.environ['LOCAL'] = str((os.getlogin() == os.environ['LOCAL_USER']))
os.environ['SERVER'] = str(not(eval(os.environ['LOCAL'])))
os.environ['PROJECT_DIR'] = os.environ['PROJECT_DIR_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['PROJECT_DIR_SERVER']
os.environ['DATA_DIR'] = os.environ['DATA_DIR_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['DATA_DIR_SERVER']
os.environ['INSCOPIX_READER']= os.environ['INSCOPIX_READER_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['INSCOPIX_READER_SERVER']
#os.environ['DECODER']= os.environ['DECODER_LOCAL'] if eval(os.environ['LOCAL']) else os.environ['DECODER_SERVER']