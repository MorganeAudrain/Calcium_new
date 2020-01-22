Radboud Memory Dynamics - Calcium Imaging Analysis
==============================
This is the main calcium imaging analysis tool for the Radboud Memory Dynamics group. The project structure is based on Cookiecutter Data Science by Driven Data. The analysis tools are provided by CaImAn by Flatiron Institute. 

This project is a joint work done by Melisa Maidana Capitan (m.maidanacapitan@donders.ru.nl), Casper ten Dam, Sebastian Tiesmeyer,  under the supervision of Francesco Battaglia. 

Project Organization
------------

    ├── LICENSE
    ├── Makefile           <- Makefile with commands like `make data` or `make train`
    ├── README.md          <- The top-level README for developers using this project.
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    │
    ├── docs               <- A default Sphinx project; see sphinx-doc.org for details
    │
    ├── models             <- Trained and serialized models, model predictions, or model summaries
    │
    ├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
    │                         the creator's initials, and a short `-` delimited description, e.g.
    │                         `1.0-jqp-initial-data-exploration`.
    │
    ├── references         <- Data dictionaries, manuals, and all other explanatory materials.
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    │
    ├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
    │                         generated with `pip freeze > requirements.txt`
    │
    ├── setup.py           <- makes project pip installable (pip install -e .) so src can be imported
    ├── src                <- Source code for use in this project.
    │   ├── __init__.py    <- Makes src a Python module
    │   │
    │   ├── data           <- Scripts to download or generate data
    │   │   └── make_dataset.py
    │   │
    │   └── visualization  <- Scripts to create exploratory and results oriented visualizations
    │       └── visualize.py

--------

This is the structure for the analysis steps of the Calcium Imaging pipeline. Here we explain steps for DATA BASE MANIPULATION, PARAMETER SELECTION AND RUNNING THE COMPLETE PIPELINE

========================================================================================================================================================================================================
STRUCTURE
=======================================================================================================================================================================================================

	├── src               					<- Source code for use in this project.
	    │   ├── steps     					<- Main codes for the different steps of the pipeline
	    │   │     └── decoding.py
	    │   │     └── equalizer.py
	    │	│     └── cropping.py
	    │	│     └── motion_correction.py
	    │	│     └── source_extraction.py
	    │	│     └── component_evaluation.py
	    │	│     └── equalizer.py
	    │   │
	    │   ├── analysis           				<- function that are related to making assesment on the processing steps via metrics evaluation or visual inspection in figures.
	    │   │   └── figures.py     				<- functions use to plot steps like croppend imaged, filtered videos, intermediate processing, contours and traces. 
	    │   │   └── metrics.py    				<- functions containing quality measurements for some of the steps
	    │   │
	    │   └── parameters_setting  			<- Scripts to explore different parameter configuration for motion correction, source extraction and component evaluation
	    │   │    └── parameters_setting_cropping.py
	    │   │    └── parameters_setting_motion_correction.py
	    │   │    └── parameters_setting_source_extraction.py
	    │   │    └── parameters_setting_source_extraction_session_wise.py
	    │   │    └── parameters_setting_component_evaluation.py
            │	│
	    │	├──data_base_manipulation			<- Functions related to excel reading, editing and version analysis update
	    │	├──analysis_file_manipulation			<- Functions related to...(?)

========================================================================================================================================================================================================
DATA BASE ADMINISTRATION (src.data_base_manipulation)
========================================================================================================================================================================================================

The module data_base_manipulation has a set of function that are related to structure of the data base, and to manipulation of it. 
The excel sheet can be found at : /home/sebastian/Documents/Melisa/calcium_imaging_analysis/references/analysis_state_database (or in the server)

There is also a parameters data base. Parameter selection is very relevant to guaranty reliable source extraction, and it should be tuned for each mouse (and probably also for each session, trial, resting condition). To organize this, the file /home/sebastian/Documents/Melisa/calcium_imaging_analysis/references/parameters_database contains the parameter selection for each one of this. Once the parameters had been selected, they can be automatically read from this file.

--------------------------------
Important funcions data base: 
-------------------------------

	*open_analysis_states_database ===> opens an excel file as a pandas dataframe structure. This file is saved in 'references/analysis/analysis_states_database'. But the fuction actually read 			the server version. Then when you save a new one, it is saved localy and in the server. 
		    
	*append_or_to_merge_analysis_states_database ===> if a new row is created because of the selection of a new set of parameters, this function localy appends the new row to the existing 			    pandas dataframe. (this need to be saved)
		
	*save_analysis_states_database ===> once the dataframe is updated, this funcion saves the new version in the local machine and it also creates a copy in the server. 

	*select ===> selection of a particular row in a pandas dataframe. With this function user can choose the analysis versions for the particular step that is being perform and also the 			experimental atributes as mouse,session,trial,is_rest. 

		The rest of the funcions are relevant for file administration or are part of the previous funcions themself. 
	*set_version_analysis ==> once the step is computed, this funcion checks whether the used parameteres for a particular step were already used in the data base. If they were, it does nothing. 
		If they were not, the function will update the version index to a new one. Later using append_or_to_merge_analysis_states_database and save_analysis_states_database funcions the data 			base will be updated  

----------------------------------------
Important funcions parameters data base: 
----------------------------------------

	*set_parameters ===> writes the parameters selection in the '.xls' file
		    
	*get_parameters ===> reads the parameters for a particular mouse/session/trial/resting_condition/step for running the pipeline.


================================================================================================================================
FILE ADMINISTRATION
========================================================================================================================================================================================================

Each step reads and saves processing steps of the pipeline in different file format. Most of the are readable from caiman.load() or LOADmmap functions. Just to avoid confusions, here there is a general guide of the files systems.

- Original videos are stored in '.raw' file ->  This file is accessible from the Inscopix software, but thanks to the generosity of Linux/Conda and the people who did this (R and F) this files can be decoded in the pastiera computers.
- Decoded files are saved as a '.tif' file. Cropping opens and saves a '.tif' file after processing. Equalized files (IN PROGRESS) saves the file in the same format as cropping.
- Motion corrected files are stored as '.mmap' files. Motion correction opens a '.tif' and saves a '.mmap' file.
- Source extracted files are stored as '.hdf5' files. Source extraction opens a '.mmap' file and saves a '.hdf5' file.
- Component evaluated files are stores as '.hdf5' files. Component evaluation reads a '.hdf5' file and saves the results in a '.hdf5' file. 

The memory consuming components (in terms of storage) are the decoded/cropping/motion_correction/equalization parts. If used the general 5 minutes video, each one creates an ~2/3Gb file. Source extraction and component evaluation files are not tha heavy (~100Mb)


========================================================================================================================================================================================================
PARAMETER SELECTION STEP BY STEP FOR TRIAL WISE ANALYSIS (src.parameter_setting)
========================================================================================================================================================================================================

The file parameter_setting is for setting parameters in one particular trial going through all the main pipeline (SIMILAR TO THE ACTUAL TRIAL_WISE_ANALYSIS). 


Then there are four main scrips for 'trial_wise' parameters setting: 

parameters_setting_cropping , parameters_setting_motion_correction , parameters_setting_source_extraction and parameters_setting_component_evaluation

Each of them works in each trial. The idea is that in each script many parameters are tested, the state od analysis data base is updated, and some figures are plotted in order to select the best parameters for each step in the pipeline.

Nevertheless, ideally one would like to select the best parameters for the hole session. Assuming cropping and motion correction parameters work well using the same in all the session (cropping should be the same), we would work in selection the best parameters in a way to optimize the extraction in the hole session. For these, we will combine souce extraction and component evaluation in the script paramerter_setting_source_extraction_session_wise, which analysis multiple trials. Also it uses some plotting as backup for decision making in the parameter selection for all the trials. 

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1.  Decoding
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1) Decode the files. This step preferably should be done in the pastiera computer, but can be done in another one if the python environment is the proper one (ask RONNY about this, and write here how to recreate the right environment)

For decoding run function Decoder. (TO BE IMPLEMENTED, 	for now decoding can be run for one selected file in parameter_selection or for all file sof a particular mouse in trial_wise_analysis). Decoding can be run separately because it does not evolved any parameters selection, so we can create a function for decode a set of videos. 
The only relevant parameters in this case are related to downsampling which is always set to 10Hz (same downsampling that has been used in the 1 photon Caiman paper)


-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1.b.  Equalizer
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Equalization is the last added step in the pipeline. This step should be run with to main objectives. 

1) Reducing the photobleching effect (as mentioned in https://imagej.net/Bleach_Correction )
2) Have an stationary signal over different days of recoding. 

The equalization procedure consists in mapping the histogram of pixel values of one image into the histogram of the other image (see '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/equalizer/meta/figures/MonaLisa_Vincent_equalization.png' for exemplification). 

It is known that bleaching diminishes the quality of the image turning it darker. The idea here is to use the histogram of the first recording videos as a template to match the following videos.


26/11/2019 This function is under construction but will take parameters: 

	parameters_equalizer = {'make_template_from_trial': '6_R', 'equalizer': 'histogram_matching', 'histogram_step': h_step}



	#make_template_from_trial < - Refers to where the reference histogram is taking from
	#equalizer <- Sets the method to histogram matching. There are other methods like exponential fitting, or mean equalization that are not yet implemented. 
	#a part of the code also produces the histogram to verify equalization. h_step sets the sets the bin size



-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
2.  Cropping
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

USE function at:
'/home/sebastian/Documents/Melisa/calcium_imaging_analysis/SRC/parameters_setting/parameters_setting_cropping' (Run by parts)

Look at the decoded images. Run function Cropping_interval_selection. This function should open an specified decoded file, plot an image one second of the movie. The user should then specified the cropping parameters by visual inspection.

The user should specify these parameters in the command windows, and they will be automatically saved in the data base as cropping parameters for that particular mouse,session,trial,is rest.

The spatial cropping points are referred to the selected interval. y1: start point in y axes, y2: end point in y axes. z1: start point in z axes, z2: end point in z axes. 

It is better not to use time cropping. Cropping parameters are now only referred to spatial or temporal cropping. 

Cropping parameters are specified in a dictionary as follows:  

	parameters_cropping= {'crop_spatial': True, 'cropping_points_spatial': [y1, y2, z1, z2],
                      'crop_temporal': False, 'cropping_points_temporal': []}

	#cropping_points_spatial  <- 'x' and 'y' axes points for cropped selection. Everything outside the interval is cropped out 
	#cropping_points_temporal <-  temporal cropping (preferably do not use for now)

 
After that the new cropped frame will be plotted for verification that the cropping is the desired one. 

Cropping should be the same always for a particular mouse. Apply cropping to all of the files related to the same mouse. Last segment of parameters_setting_cropping sets the cropping values in the parameter database for each trial. The idea is that later, in the complete pipeline, parameters are read from the parameters data base. 

Version selection: As implemented in the data base, there is a control for versions and parameters. The function set_version_analysis verifies whether the selected parameters for current cropping points were already used or not. If not used, it increase in one the last version, and then the new row is added to the data base, with the new parameters dictonary included.
Version selection is run inside the cropper function. 
Important : Even the cropping parameters should be the same for all trials of a mouse, version selection should be run one by one (just in case there is a previous version with the new parameters)

TEST CROPPING: parameter_setting scripts can be run in a small section of the filed of view (FOV) in order to be able to run faster multiple motion correction and source extraction parameters. But, it needs to be verified that the convergence of an extended area of the FOV will return ~ the same neural footprints. For that, may use of script in parameters_setting_cropping_impact. 
In this script we select 5 different cropping with different sizes, and run the pipeline (with out component evaluation). That output is a figure that is saved in  directory = '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/cropping/meta/figures/cropping_initialization/'. This figure contains tha contour plots for different cropping, but always using the same motion correction and source extraction parameters. This step is important because the algorithm is really sensitive to changes in the seed or initial condition. Changes in the size of the FOV of course will lead to changes in the initial condition, that can lead to huge differences in the extraction. Do not forget to verify before generalizing your parameters to a bigger FOV. 


-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
3. Motion correction
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

USE script at:
'/home/sebastian/Documents/Melisa/calcium_imaging_analysis/SRC/parameters_setting/parameters_setting_motion_correction'

Motion correction can be run both in the server and it the local machine, but it is supposed to be faster in the server. 

Motion correction parameters as specified in a dictionary as follows : 

	parameters_motion_correction = {'motion_correct': True, 'pw_rigid': True, 'save_movie_rig': False,
              'gSig_filt': (7, 7), 'max_shifts': (25, 25), 'niter_rig': 1, 'strides': (96, 96),
              'overlaps': (48, 48), 'upsample_factor_grid': 2, 'num_frames_split': 80, 'max_deviation_rigid': 15,
              'shifts_opencv': True, 'use_cuda': False, 'nonneg_movie': True, 'border_nan': 'copy'}

	# motion correction parameters
	motion_correct = True    # flag for performing motion correction
	pw_rigid = True          # flag for performing piecewise-rigid motion correction (otherwise just rigid)
	gSig_filt = (3, 3)       # size of high pass spatial filtering, used in 1p data
	max_shifts = (5, 5)      # maximum allowed rigid shift
	strides = (48, 48)       # start a new patch for pw-rigid motion correction every x pixels
	overlaps = (24, 24)      # overlap between pathes (size of patch strides+overlaps)
	max_deviation_rigid = 3  # maximum deviation allowed for patch with respect to rigid shifts
	border_nan = 'copy'      # replicate values along the boundaries


This script runs a few examples of gSig_filt size and saves the figure in folder: 

'/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/motion_correction/meta/figures'

for each mouse,session,trial,is_rest parameters and version analysis. 

Once several parameters of motion_correction had been run, it is necessary to compare performance. Easier quality measurement of motion correction is crispness. And the end the script goes over all the analysed motion corrected versions (using function compare_crispness that is defined in analysis.metrics), and with plot_crispness_for_parameters (analysis.figures) creates a plot for cripness for the mean summary image and for the corr summary image. 


Also the script can run several rigid mode, pw_rigid modes, or other variations of the parameters. 

Strides size and overlap are relevant parameters if 'pw_rigid' mode is use. 

Optimal parameters correspond to --- values of crispness. The script prints in the screen the full dictionary corresponding to the optimal ones. 

(Ideally this should be save in the parameters data base, to be read later and directly implemented in the pipeline...for now, let's do it manually)

Ready for next step.

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
4. Source extraction
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

USE script at:
'/home/sebastian/Documents/Melisa/calcium_imaging_analysis/SRC/parameters_setting/parameters_setting_source_extraction'

Source extraction can be run both in the server and it the local machine, but again it is supposed to be faster in the server. 

Source extraction parameters as specified in a dictionary as follows : 

	parameters_source_extraction ={'session_wise': False, 'fr': 10, 'decay_time': 0.1, 'min_corr': 0.77, 'min_pnr': 6.6,
                               'p': 1, 'K': None, 'gSig': (5, 5), 'gSiz': (20, 20), 'merge_thr': 0.7, 'rf': 60,
                               'stride': 30, 'tsub': 1, 'ssub': 2, 'p_tsub': 1, 'p_ssub': 2, 'low_rank_background': None,
                               'nb': 0, 'nb_patch': 0, 'ssub_B': 2, 'init_iter': 2, 'ring_size_factor': 1.4,
                               'method_init': 'corr_pnr', 'method_deconvolution': 'oasis',
                               'update_background_components': True,
                               'center_psf': True, 'border_pix': 0, 'normalize_init': False,
                               'del_duplicates': True, 'only_init': True}

	# parameters for source extraction and deconvolution
	p = 1               # order of the autoregressive system
	K = None            # upper bound on number of components per patch, in general None
	gSig = (3, 3)       # gaussian width of a 2D gaussian kernel, which approximates a neuron
	gSiz = (13, 13)     # average diameter of a neuron, in general 4*gSig+1
	Ain = None          # possibility to seed with predetermined binary masks
	merge_thr = .7      # merging threshold, max correlation allowed
	rf = 40             # half-size of the patches in pixels. e.g., if rf=40, patches are 80x80
	stride_cnmf = 20    # amount of overlap between the patches in pixels
	#                     (keep it at least large as gSiz, i.e 4 times the neuron size gSig)
	tsub = 2            # downsampling factor in time for initialization,
	#                     increase if you have memory problems
	ssub = 1            # downsampling factor in space for initialization,
	#                     increase if you have memory problems
	#                     you can pass them here as boolean vectors
	low_rank_background = None  # None leaves background of each patch intact,
	#                     True performs global low-rank approximation if gnb>0
	gnb = 0             # number of background components (rank) if positive,
	#                     else exact ring model with following settings
	#                         gnb= 0: Return background as b and W
	#                         gnb=-1: Return full rank background B
	#                         gnb<-1: Don't return background
	nb_patch = 0        # number of background components (rank) per patch if gnb>0,
	#                     else it is set automatically
	min_corr = .8       # min peak value from correlation image
	min_pnr = 10        # min peak to noise ration from PNR image
	ssub_B = 2          # additional downsampling factor in space for background
	ring_size_factor = 1.4  # radius of ring is gSiz*ring_size_factor


The script runs different selections of gSig (gSiz = 4 * gSig + 1) and saves the resulting corr and pnr summary image (as well as the combination) in '/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/source_extraction/trial_wise/meta/figures/corr_pnr/'. From here exploration of the effect of different gSig on the summary images can be done.

Later exploration of min_corr and min_pnr can be done. The scripts creates a bunch of histograms to get an intuitive idea of the values of corr and pnr of a video. 

Selection a range or corr and pnr values, there is a script that computes source extraction and plots a figure with all the contour plots for the analyzed parameters. This plotting helps to understand how initial seeds change the final result of the extraction.  

Visual inspection of this figure can help to decide which values of pnr and corr are adequate (selects the higher number of neurons that are 'real neurons'). Parameter selection of source extraction can be done in combination with parameter selection of component evaluation in order to get a better solution.

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
5. Component Evaluation
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
USE script at:
'/home/sebastian/Documents/Melisa/calcium_imaging_analysis/SRC/parameters_setting/parameters_setting_component_evaluation'

For running component evaluation a version of all previous states should be chosen. This step can be run in the local machine.

Component evaluation parameters are 3: minimal value of signal to noise ration in the extracted calcium traces, minimal pearson correlation coefficient between a template for the 'neuron footprint' extracted as a mean over all the images and the source extracted footprint, and a boolean variable that specifies whether the assessment will or will not use a CNN for classification as good/bad component.

Componente evaluation parameters as specified in a dictionary as follows : 

	parameters_component_evaluation = {'min_SNR': 3,
                                   'rval_thr': 0.85,
                                   'use_cnn': False}


The script proposed runs for all source extraction versions selected different selection of component evaluation parameters and makes some plot where accepted and rejected components can be seen in the contour plot and also in  the traces ( plot_contours_evaluated and plot_traces_multiple_evaluated)



========================================================================================================================================================================================================
PARAMETER SELECTION FOR SESSION (or day) WISE ANALYSIS (src.parameter_setting)
========================================================================================================================================================================================================

Bleaching effect ===> Because of continuous exposure to the light of the microscope, the image gets bleached. The effect of the bleaching can be seen in figures save in the folders: 

'/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/source_extraction/session_wise/meta/figures/contours/'

and

'/home/sebastian/Documents/Melisa/calcium_imaging_analysis/data/interim/source_extraction/trial_wise/meta/figures/fig:corrpnrphotobleaching56165.png'

In the later the mean of the pnr and correlation image is taken, and the figure shows the evaluation of the mean value over different days (Implement this as a separate part from source extraction to make it faster, because only the corr and pnr image are required).

In the first folder, there are different figures that shows the bleaching effect in the source extraction by showing the contours of different trials within a day and using different parameters for the extraction. Visual inspection can show that during the first trial more neurons are detected, and during late trials that corr image gets blurier and less amount of neurons are detected. 

Next problem is then how to select source extraction parameters (and component evaluation parameters) that are useful for all the days, and that are chosen with a 'good enough' criteria. Three different paths are being explore here. 


1) Looking for optimality ===> Use the same parameter for every day. For doing so, source extraction and component evaluation is performed in a small cropped region with a intensive parameter exploration. First idea is to select the source extraction and component evaluation parameters that near to a border transition from accepting every neuron in the last day maximize the cell counting in the last days while minimizing the false positive counting (using same source extraction and component evaluation params) in the first day.

2) Template matching ===> Based on the assumption that if a neuron is detected during the first trial, it should also be there for the later trials, once parameters for the first trial has been selected, use the neural footprint as a template for the other trials. For this, make an exploration of source extraction parameters during every other trial and select the one that maximizes overlapping or matching between new selected neurons and the ones selected during the first trial.

3) Source extraction of all the trials together. For this, it is important first to do the alignment between different trials. Use motion correction for alignment and run source extraction and component evaluation for everything together. NEW SUGGESTION BT F.STELLA (IN DEVELOPMENT): Verify source extraction during resting periods. 	 

4) IN DEVELOPMENT (20/11/19) -> equalization and histogram matching of videos. 

Finally, compare the results ==> compare cell counting, final footprints and calcium traces ! 


========================================================================================================================================================================================================
RUNNING THE COMPLETE PIPELINE STEP BY STEP
========================================================================================================================================================================================================


Once parameters are selected...Run the pipeline with all the steps with the best parameters, all the trials and resting/non resting conditions, all the sessions, all the mice! HAPPY :) 


