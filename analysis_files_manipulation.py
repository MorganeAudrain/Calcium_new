
import os
import logging
import numpy as np
import caiman as cm
import datetime
import pickle
import data_base_manipulation as db

def get_corr_pnr(index, row, gSig=None):
    ''' This function gets an analysis state and a gSig absolute value
    and creates correlation and pnr images for it.'''
    # Define data directory
    data_dir = 'data/interim/source_extraction/trial_wise/'
    if type(gSig) == type(None):
        gSig = db.get_parameters('source_extraction', index[0], index[1], index[2], index[3])['gSig'][0]

    motion_correction_output = eval(row['motion_correction_output'])
    input_mmap_file_path = motion_correction_output['main']
    # Compute summary images
    t0 = datetime.datetime.today()
    logging.info(f'{index} Computing summary images')

    if os.path.isfile(input_mmap_file_path):
        Yr, dims, T = cm.load_memmap(input_mmap_file_path)
        logging.debug(f'{index} Loaded movie. dims = {dims}, T = {T}.')
        images = Yr.T.reshape((T,) + dims, order='F')
    else:
        logging.warning(f'{index} .mmap file does not exist. Cancelling')
        return index, row
    cn_filter, pnr = cm.summary_images.correlation_pnr(images[::1], gSig=gSig, swap_dim=False)
    dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
    logging.info(f'{index} Computed summary images. dt = {dt} min')
    # Saving summary images as npy files
    corr_npy_file_path = data_dir + f'meta/corr/{db.create_file_name(3, index)}_gSig_{gSig}.npy'
    pnr_npy_file_path = data_dir + f'meta/pnr/{db.create_file_name(3, index)}_gSig_{gSig}.npy'

    with open(corr_npy_file_path, 'wb') as f:
        np.save(f, cn_filter)

    with open(pnr_npy_file_path, 'wb') as f:
        np.save(f, pnr)

    # Define the source extraction output already
    output = {'meta': {}}
    # Store the paths in the meta dictionary
    output['meta']['corr'] = {'main': corr_npy_file_path, 'meta': {}}
    output['meta']['pnr'] = {'main': pnr_npy_file_path, 'meta': {}}
    # Get the min, mean, max
    output['meta']['corr']['min'] = round(cn_filter.min(), 3)
    output['meta']['corr']['mean'] = round(cn_filter.mean(), 3)
    output['meta']['corr']['max'] = round(cn_filter.max(), 3)
    output['meta']['pnr']['min'] = round(pnr.min(), 2)
    output['meta']['pnr']['mean'] = round(pnr.mean(), 2)
    output['meta']['pnr']['max'] = round(pnr.max(), 2)

    # Store the output in the row
    row.loc['source_extraction_output'] = str(output)
    return index, row


def get_corr_pnr_path(index, gSig_abs=None):
    fname = db.create_file_name(2, index)
    os.chdir(os.environ['PROJECT_DIR'])
    corr_dir = 'data/interim/source_extraction/trial_wise/meta/corr'
    corr_path = None
    for path in os.listdir(corr_dir):
        if fname in path:
            if gSig_abs == None:
                corr_path = os.path.join(corr_dir, path)
            else:
                if path[-5] == str(gSig_abs):
                    corr_path = os.path.join(corr_dir, path)
    pnr_dir = 'data/interim/source_extraction/trial_wise/meta/pnr'
    pnr_path = None
    for path in os.listdir(pnr_dir):
        if fname in path:
            if gSig_abs == None:
                pnr_path = os.path.join(pnr_dir, path)
            else:
                if path[-5] == str(gSig_abs):
                    pnr_path = os.path.join(pnr_dir, path)

    return corr_path, pnr_path


def get_quality_metrics_motion_correction(row, crispness=False, local_correlations=False, correlations=False,
                optical_flow=False):
    '''
    This is a wrapper function to compute (a selection of) the metrics provided
    by CaImAn for motion correction.
    '''
    # Get the parameters, motion correction output and cropping output of this row
    index = row.name
    row_local = row.copy()
    parameters = eval(row_local.loc['motion_correction_parameters'])
    output = eval(row_local.loc['motion_correction_output'])
    cropping_output = eval(row_local.loc['cropping_output'])
    # Get the metrics file path
    metrics_pkl_file_path = output['meta']['metrics']['other']
    # Load the already available metrics
    with open(metrics_pkl_file_path, 'rb') as f:
        try:
            meta_dict = pickle.load(f)
        except:
            meta_dict = {}

    # ORIGINAL MOVIE
    logging.info(f'{index} Computing metrics for original movie')
    t0 = datetime.datetime.today()
    fname_orig = cropping_output['main']
    tmpl_orig, crispness_orig, crispness_corr_orig, correlations_orig, img_corr_orig, flows_orig, norms_orig = get_metrics_auxillary(
        fname_orig, swap_dim=False, winsize=100, play_flow=False,
        resize_fact_flow=.2, one_photon=True, crispness=crispness,
        correlations=correlations, local_correlations=local_correlations,
        optical_flow=optical_flow)
    dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
    output['meta']['metrics']['original'] = {
        'crispness': crispness_orig,
        'crispness_corr': crispness_corr_orig
    }
    meta_dict['original'] = db.remove_None_from_dict({
        'correlations': correlations_orig,
        'local_correlations': img_corr_orig,
        'flows': flows_orig,
        'norms': norms_orig})
    output['meta']['duration']['metrics_orig'] = dt
    logging.info(f'{index} Computed metrics for original movie. dt = {dt} min')

    # RIGID MOVIE
    if not parameters['pw_rigid'] or (parameters['pw_rigid'] and 'alternate' in output):
        logging.info(f'{index} Computing metrics for rigid movie')
        t0 = datetime.datetime.today()
        fname_rig = output['main'] if not parameters['pw_rigid'] else output['alternate']
        tmpl_rig, crispness_rig, crispness_corr_rig, correlations_rig, img_corr_rig, flows_rig, norms_rig = get_metrics_auxillary(
            fname_rig, swap_dim=False, winsize=100, play_flow=False,
            resize_fact_flow=.2, one_photon=True, crispness=crispness,
            correlations=correlations, local_correlations=local_correlations,
            optical_flow=optical_flow)
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        output['meta']['metrics']['rigid'] = {
            'crispness': crispness_rig,
            'crispness_corr': crispness_corr_rig
        }
        meta_dict['rigid'] = db.remove_None_from_dict({
            'correlations': correlations_rig,
            'local_correlations': img_corr_rig,
            'flows': flows_rig,
            'norms': norms_rig})
        output['meta']['duration']['metrics_rig'] = dt
        logging.info(f'{index} Computed metrics for rigid movie. dt = {dt} min')

    if parameters['pw_rigid']:
        logging.info(f'{index} Computing metrics for pw-rigid movie')
        t0 = datetime.datetime.today()
        fname_els = output['main']
        tmpl_els, crispness_els, crispness_corr_els, correlations_els, img_corr_els, flows_els, norms_els = get_metrics_auxillary(
            fname_els, swap_dim=False, winsize=100, play_flow=False,
            resize_fact_flow=.2, one_photon=True, crispness=crispness,
            correlations=correlations, local_correlations=local_correlations,
            optical_flow=optical_flow)
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        output['meta']['metrics']['pw_rigid'] = {
            'crispness': crispness_els,
            'crispness_corr': crispness_corr_els
        }
        meta_dict['pw_rigid'] = db.remove_None_from_dict({
            'correlations': correlations_els,
            'local_correlations': img_corr_els,
            'flows': flows_els,
            'norms': norms_els})
        output['meta']['duration']['metrics_els'] = dt
        logging.info(f'{index} Computed metrics for pw-rigid movie. dt = {dt} min')

        # Save the metrics in a pkl file
    logging.info(f'{index} Saving metrics')
    with open(metrics_pkl_file_path, 'wb') as f:
        pickle.dump(meta_dict, f)
    logging.info(f'{index} Saved metrics')

    # Store the new output and return it
    row_local.loc['motion_correction_output'] = str(output)
    return row_local

def get_metrics_auxillary(fname, swap_dim, pyr_scale=.5, levels=3,
                          winsize=100, iterations=15, poly_n=5, poly_sigma=1.2 / 5, flags=0,
                          play_flow=False, resize_fact_flow=.2, template=None, save_npz=False,
                          one_photon=True, crispness=True, correlations=True, local_correlations=True,
                          optical_flow=True):
    '''
    This function is actually copied from the CaImAn packages and edited for use in this calcium
    imaging analysis pipeline. It contained some abnormalities that we wanted to avoid.
    '''
    import scipy
    import cv2

    # Logic
    if crispness: local_correlations = True

    # Load the movie
    m = cm.load(fname)
    vmin, vmax = -1, 1

    #    max_shft_x = np.int(np.ceil((np.shape(m)[1] - final_size_x) / 2))
    #    max_shft_y = np.int(np.ceil((np.shape(m)[2] - final_size_y) / 2))
    #    max_shft_x_1 = - ((np.shape(m)[1] - max_shft_x) - (final_size_x))
    #    max_shft_y_1 = - ((np.shape(m)[2] - max_shft_y) - (final_size_y))
    #    if max_shft_x_1 == 0:
    #        max_shft_x_1 = None
    #
    #    if max_shft_y_1 == 0:
    #        max_shft_y_1 = None
    #    logging.info([max_shft_x, max_shft_x_1, max_shft_y, max_shft_y_1])
    #    m = m[:, max_shft_x:max_shft_x_1, max_shft_y:max_shft_y_1]

    # Check the movie for NaN's which may cause problems
    if np.sum(np.isnan(m)) > 0:
        logging.info(m.shape)
        logging.warning('Movie contains NaN')
        raise Exception('Movie contains NaN')

    if template is None:
        tmpl = cm.motion_correction.bin_median(m)
    else:
        tmpl = template

    if correlations:
        logging.debug('Computing correlations')
        t0 = datetime.datetime.today()
        correlations = []
        count = 0
        if one_photon:
            m_compute = m - np.min(m)
        for fr in m_compute:
            if count % 100 == 0:
                logging.debug(f'Frame {count}')
            count += 1
            correlations.append(scipy.stats.pearsonr(
                fr.flatten(), tmpl.flatten())[0])
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        logging.debug(f'Computed correlations. dt = {dt} min')
    else:
        correlations = None

    if local_correlations:
        logging.debug('Computing local correlations')
        t0 = datetime.datetime.today()
        img_corr = m.local_correlations(eight_neighbours=True, swap_dim=swap_dim)
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        logging.debug(f'Computed local correlations. dt = {dt} min')
    else:
        img_corr = None

    if crispness:
        logging.debug('Computing crispness')
        t0 = datetime.datetime.today()
        smoothness = np.sqrt(
            np.sum(np.sum(np.array(np.gradient(np.mean(m, 0))) ** 2, 0)))
        smoothness_corr = np.sqrt(
            np.sum(np.sum(np.array(np.gradient(img_corr)) ** 2, 0)))
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        logging.debug(
            f'Computed crispness. dt = {dt} min. Crispness = {smoothness}, crispness corr = {smoothness_corr}.')
    else:
        smoothness = None

    if optical_flow:
        logging.debug('Computing optical flow')
        t0 = datetime.datetime.today()
        m = m.resize(1, 1, resize_fact_flow)
        norms = []
        flows = []
        count = 0
        for fr in m:
            if count % 100 == 0:
                logging.debug(count)

            count += 1
            flow = cv2.calcOpticalFlowFarneback(
                tmpl, fr, None, pyr_scale, levels, winsize, iterations, poly_n, poly_sigma, flags)

            if play_flow:
                pl.subplot(1, 3, 1)
                pl.cla()
                pl.imshow(fr, vmin=0, vmax=300, cmap='gray')
                pl.title('movie')
                pl.subplot(1, 3, 3)
                pl.cla()
                pl.imshow(flow[:, :, 1], vmin=vmin, vmax=vmax)
                pl.title('y_flow')

                pl.subplot(1, 3, 2)
                pl.cla()
                pl.imshow(flow[:, :, 0], vmin=vmin, vmax=vmax)
                pl.title('x_flow')
                pl.pause(.05)

            n = np.linalg.norm(flow)
            flows.append(flow)
            norms.append(n)
        dt = int((datetime.datetime.today() - t0).seconds / 60)  # timedelta in minutes
        logging.debug(f'Computed optical flow. dt = {dt} min')
    else:
        flows = norms = None

    if save_npz:
        logging.debug('Saving metrics in .npz format')
        np.savez(fname[:-4] + '_metrics', flows=flows, norms=norms, correlations=correlations, smoothness=smoothness,
                 tmpl=tmpl, smoothness_corr=smoothness_corr, img_corr=img_corr)
        logging.debug('Saved metrics in .npz format')

    return tmpl, smoothness, smoothness_corr, correlations, img_corr, flows, norms


#
# def get_corr_pnr(index, row):
#    '''
#    This function computes the correlation and pnr images as numpy arrays for a motion corrected
#    movie which can be used to set source extraction parameters and in source
#    extraction itself, namely for initialization.
#    '''
#    # Get the parameters, motion correction output and cropping output of this row
#    parameters = eval(row.loc['motion_correction_parameters'])
#    output =  eval(row.loc['motion_correction_output'])
#    cropping_output = eval(row.loc['cropping_output'])
#
#    # Determine the corr_pnr file path
#    fname = db.create_file_name(2, index)
#    corr_path = f'data/interim/motion_correction/meta/corr/{fname}.npy'
#    pnr_path = f'data/interim/motion_correction/meta/pnr/{fname}.npy'
#
#
#    logging.info(f'{index} Computing correlation and pnr images for movie')
#    t0 = datetime.datetime.today()
#    m_path = output['main']
#    tmpl_els, crispness_els, crispness_corr_els, correlations_els, img_corr_els, flows_els, norms_els = get_metrics_auxillary(
#            fname_els, swap_dim = False, winsize = 100, play_flow=False,
#            resize_fact_flow = .2,  one_photon = True, crispness = crispness,
#            correlations = correlations, local_correlations = local_correlations,
#            optical_flow = optical_flow)
#
#    dt = int((datetime.datetime.today() - t0).seconds/60) # timedelta in minutes
#    meta_dict['pw_rigid'] = db.remove_None_from_dict({
#            'crispness': crispness_els,
#            'crispness_corr':crispness_corr_els,
#            'correlations': correlations_els,
#            'local_correlations': img_corr_els,
#            'flows': flows_els,
#            'norms': norms_els })
#    output['meta']['duration']['corr_pnr'] = dt
#    logging.info(f'{index} Computed correlation and pnr images for movie. dt = {dt} min')
#
#    # Save the metrics in a pkl file
#    logging.info(f'{index} Saving metrics')
#    with open(metrics_pkl_file_path, 'wb') as f:
#        pickle.dump(meta_dict, f)
#    logging.info(f'{index} Saved metrics')
#
#    # Store the new output in the master file list
#    row.loc['motion_correction_output'] = str(output)
# master_df = db.open_analysis_states_database()
# master_df = db.append_to_or_merge_with_states_df(master_df, row)
#    return

# %% FIGURES


# def get_figs(index, row, save_fig = False):
#     # Define the figure title
#    fig_title = 'Metrics'
#
#    ## GET THE DATA
#    # Get the mouse and session
#    mouse, session = (index[i] for i in [0,1])
#    # Load the metrics
#    with open(output['meta']['metrics'], 'rb') as f:
#        metrics = pickle.load(f)
#
#    ## CREATE THE FIGURE
#    # Create the figure
#    fig, axes = plt.subplots(4, 3)
#    # Set the figure size
#    fig.set_size_inches(15., 15.)
#    # Plot shifts
#
#
#    # Plot min, mean and max values
#    ax_min.plot(a_min)
#    ax_mean.plot(a_mean)
#    ax_max.plot(a_max)
#    # Set the labels
#    ax_min.set_xlabel('frames') ; ax_mean.set_xlabel('frames') ; ax_max.set_xlabel('frames')
#    ax_min.set_ylabel('min') ; ax_mean.set_ylabel('mean') ; ax_max.set_ylabel('max')
#    # Get the xticks
#    ax_min_xticks, ax_mean_xticks, ax_max_xticks = (ax.get_xticks() for ax in [ax_min, ax_mean, ax_max])
#    # Get the xlabels
#    ax_min_xticklabels, ax_mean_xticklabels, ax_max_xticklabels = (ax.get_xticklabels() for ax in [ax_min, ax_mean, ax_max])
#    # Append the movie starting points to the xticks
#    ax_min_xticks = np.append(ax_min_xticks, a_starting_points[:,1]) ; ax_mean_xticks = np.append(ax_mean_xticks, a_starting_points[:,1]) ; ax_max_xticks =  np.append(ax_max_xticks, a_starting_points[:,1])
#    # Append the trial names to the xticklabels
#    ax_min_xticklabels = np.append(ax_min_xticklabels, a_starting_points[:,0]) ; ax_mean_xticklabels = np.append(ax_mean_xticklabels, a_starting_points[:,0]) ; ax_max_xticklabels = np.append(ax_max_xticklabels, a_starting_points[:,0])
#    # Set the xticks
#    ax_min.set_xticks(ax_min_xticks) ; ax_mean.set_xticks(ax_mean_xticks) ; ax_max.set_xticks(ax_max_xticks)
#    # Set the xticklabels
#    ax_min.set_xticklabels(ax_min_xticklabels) ; ax_mean.set_xticklabels(ax_mean_xticklabels) ; ax_max.set_xticklabels(ax_max_xticklabels)
#    # Set the y limits
#    for i, ax in enumerate(axes): ax.set_ylim(np.percentile(arrays[i], .1), np.percentile(arrays[i], 99.99))
#    # Set the figure plot
#    fig.suptitle(f"{fig_title} \n step: {step} \n data: ({mouse}, {session})")
#    if save_fig:
#        # Define the figure directory
#        fig_dir = 'data/interim/decoding/meta/figures/session_wise/min_mean_max/'
#        # Save the figure
#        fig.savefig(fig_dir + db.create_file_name(step_index, index) + '.png')
#

def make_figures(index, row, force=False):
    # Create file name
    file_name = db.create_file_name(step_index, index)

    # Load meta_pkl file
    output = eval(row.loc['motion_correction_output'])
    metrics_pkl_file_path = output['meta']['metrics']
    with open(metrics_pkl_file_path, 'rb') as f:
        x = pickle.load(f)

    # Possible figures
    figure_names = np.array(['rig_template', 'rig_shifts', 'els_template', 'correlations', 'corelations_orig_vs_rig',
                             'correlations_rig_vs_els', 'correlations_orig_vs_els', 'orig_local_correlations',
                             'rig_local_correlations',
                             'els_local_correlations'])

    def figure_flag(i):
        # This function determines which figures can be made. If they cannot be made, either
        # an analysis step has not been performed or metrics have to be computed
        if i == 0:
            return 'rigid' in x
        elif i == 1:
            return 'rigid' in x
        elif i == 2:
            return 'non-rigid' in x
        elif i == 3:
            return ['original' in x and 'correlations' in x['original'], 'rigid' in x and 'correlations' in x['rigid'],
                    'non-rigid' in x and 'correlations' in x['non-rigid']]
        elif i == 4:
            return ('original' in x and 'correlations' in x['original']) and (
                        'rigid' in x and 'correlations' in x['rigid'])
        elif i == 5:
            return ('non-rigid' in x and 'correlations' in x['non-rigid']) and (
                        'rigid' in x and 'correlations' in x['rigid'])
        elif i == 6:
            return ('original' in x and 'correlations' in x['original']) and (
                        'non-rigid' in x and 'correlations' in x['non-rigid'])
        elif i == 7:
            return 'original' in x and 'local_correlations' in x['original']
        elif i == 8:
            return 'rigid' in x and 'local_correlations' in x['rigid']
        elif i == 9:
            return 'non-rigid' in x and 'local_correlations' in x['non-rigid']

    def make_figure(i):
        # This function specifies how each of the figures are layed out
        if i == 0:
            plt.imshow(x['rigid']['total_template'], cmap='gray');
            plt.title('Total template rigid motion correction')
        elif i == 1:
            plt.plot(x['rigid']['shifts']);
            plt.legend(['x shifts', 'y shifts']);
            plt.xlabel('frames');
            plt.ylabel('pixels');
            plt.title('Shifts rigid motion correction')
        elif i == 2:
            plt.imshow(x['non-rigid']['total_template'], cmap='gray');
            plt.title('Total template piecewise-rigid motion correction')
        elif i == 3:
            legend = []
            for idx, flag in enumerate(figure_flag(i)):
                if flag:
                    string = ['original', 'rigid', 'non-rigid'][idx]
                    legend += string
                    plt.plot(x[string]['correlations'])
                plt.xlabel('frames')
                plt.legend(legend)
                plt.title('Correlations')
        elif i == 4:
            min_cor, max_cor = min(x['original']['correlations'] + x['rigid']['correlations']), max(
                x['original']['correlations'] + x['rigid']['correlations'])
            plt.scatter(x['original']['correlations'], x['rigid']['correlations']);
            plt.xlabel('original');
            plt.ylabel('rigid');
            plt.plot([min_cor, max_cor], [min_cor, max_cor], 'r--')
            plt.title('Original v. rigid correlations')
        elif i == 5:
            min_cor, max_cor = min(x['rigid']['correlations'] + x['non-rigid']['correlations']), max(
                x['rigid']['correlations'] + x['non-rigid']['correlations'])
            plt.scatter(x['rigid']['correlations'], x['non-rigid']['correlations']);
            plt.xlabel('rigid');
            plt.ylabel('non-rigid');
            plt.plot([min_cor, max_cor], [min_cor, max_cor], 'r--')
            plt.title('Rigid v. piecewise-rigid correlations')
        elif i == 6:
            min_cor, max_cor = min(x['original']['correlations'] + x['non-rigid']['correlations']), max(
                x['original']['correlations'] + x['non-rigid']['correlations'])
            plt.scatter(x['original']['correlations'], x['non-rigid']['correlations']);
            plt.xlabel('original');
            plt.ylabel('non-rigid');
            plt.plot([min_cor, max_cor], [min_cor, max_cor], 'r--')
            plt.title('Original v. piecewise-rigid correlations')
        elif i == 7:
            plt.imshow(x['original']['local_correlations']);
            plt.title('Local correlations original movie')
        elif i == 8:
            plt.imshow(x['rigid']['local_correlations']);
            plt.title('Local correlations rigid motion correction')
        elif i == 9:
            plt.imshow(x['non-rigid']['local_correlations']);
            plt.title('Local correlations piecewise-rigid motion correction')

    for i in range(0, len(figure_names)):
        if (figure_flag(i) if i != 3 else (True in figure_flag(i))):
            plt.figure()
            make_figure(i)
            plt.savefig(f'data/interim/motion_correction/meta/figures/{file_name}_{figure_names[i]}.png')
            plt.close()

    return


def parameters_test_gSig(path, figname, gSig_filt_list=None):
    m_orig = cm.load(path)

    if gSig_filt_list == None:
        gSig_filt_list = [(2, 2), (4, 4), (6, 6), (8, 8), (10, 10), (20, 20), (30, 30)]
    m_filt_list = []
    for i, gSig_filt in enumerate(gSig_filt_list):
        m_filt_list.append(cm.movie(np.array([high_pass_filter_space(m_, gSig_filt) for m_ in m_orig])))

    import matplotlib.pyplot as plt
    for i, mov in enumerate(m_filt_list):
        plt.figure()
        plt.imshow(mov[0], cmap='gray')
        gSig_size = gSig_filt_list[i]
        plt.title(f'{figname} \n gSig_size = {gSig_size}')
        plt.savefig(f'data/motion_correction/png/{figname}_gSig_experiment_{gSig_size}.png')

    return


# def get_fig_gSig_filt(im, gSig_filt, fig_index = None, cmap = 'gray'):
#
#    im_filter = high_pass_filter_space(im, gSig_filt)
#    if fig_index == None:
#        fig = plt.figure()
#    else:
#        fig = plt.figure(fig_index)
#    ax.imshow(im_filter, cmap = cmap)
#    fig.colorbar()
#    ax.title(f'gSig_filt = {gSig_filt}')
#
#    return fig
#

def get_fig_patches(im, strides, overlaps, cmap='gray'):
    patches = (strides[0] + overlaps[0], strides[1] + overlaps[1])

    fig, ax = plt.subplots(1)
    plt.imshow(im, cmap=cmap)
    #    plt.title(f'Patches: {patches}, strides: {strides}, overlaps: {overlaps}')

    shape = im.shape
    nr_of_patches_x = int(shape[0] / strides[0])
    nr_of_patches_y = int(shape[1] / strides[1])

    for i in range(0, nr_of_patches_x):
        for j in range(0, nr_of_patches_y):
            rect = Rectangle((j * strides[1], i * strides[0]), patches[1], patches[0], fill=True,
                             ec='black', fc='r', linestyle='-', alpha=0.2)
            ax.add_patch(rect)
    ax.axis('off')

    return fig


def get_fig_gSig_filt_vals(m, gSig_filt_vals):
    temp = cm.motion_correction.bin_median(m)
    N = len(gSig_filt_vals)
    fig, axes = plt.subplots(int(math.ceil((N + 1) / 4)), 4)
    axes[0, 0].imshow(temp, cmap='gray')
    axes[0, 0].set_title('unfiltered')
    axes[0, 0].axis('off')
    for i in range(0, N):
        gSig_filt = gSig_filt_vals[i]
        m_filt = [high_pass_filter_space(m_, (gSig_filt, gSig_filt)) for m_ in m]
        temp_filt = cm.motion_correction.bin_median(m_filt)
        axes.flatten()[i + 1].imshow(temp_filt, cmap='gray')
        axes.flatten()[i + 1].set_title(f'gSig_filt = {gSig_filt}')
        axes.flatten()[i + 1].axis('off')
    if N + 1 != axes.size:
        for i in range(N + 1, axes.size):
            axes.flatten()[i].axis('off')

    return fig

