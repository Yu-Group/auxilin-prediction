import os
import sys
from copy import deepcopy
from os.path import join as oj

sys.path.append('..')
import mat4py
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from skimage.external.tifffile import imread

pd.options.mode.chained_assignment = None  # default='warn' - caution: this turns off setting with copy warning
import pickle as pkl
from viz import *
import math
import config
import features
import outcomes
import load_tracking

def get_data(dset='clath_aux+gak_a7d2', use_processed=True, save_processed=True,
             processed_file=oj(config.DIR_PROCESSED, 'df.pkl'),
             metadata_file=oj(config.DIR_PROCESSED, 'metadata.pkl'),
             use_processed_dicts=True,
             outcome_def='y_consec_thresh', all_data=False, acc_thresh=0.95,
             previous_meta_file=None):
    '''
    Params
    ------
    use_processed: bool, optional
        determines whether to load df from cached pkl
    save_processed: bool, optional
        if not using processed, determines whether to save the df
    use_processed_dicts: bool, optional
        if False, recalculate the dictionary features
    previous_meta_file: str, optional
        filename for metadata.pkl file saved by previous preprocessing
        the thresholds for lifetime are taken from this file
    '''
    # get things based onn dset
    DSET = config.DSETS[dset]
    LABELS = config.LABELS[dset]

    processed_file = processed_file[:-4] + '_' + dset + '.pkl'
    metadata_file = metadata_file[:-4] + '_' + dset + '.pkl'

    if use_processed and os.path.exists(processed_file):
        return pd.read_pickle(processed_file)
    else:
        print('loading + preprocessing data...')
        metadata = {}
        print('\tloading tracks...')
        df = load_tracking.get_tracks(data_dir=DSET['data_dir'], split=DSET, all_data=all_data,
                        dset=dset)  # note: different Xs can be different shapes
#         df = df.fillna(df.median()) # this only does anything for the dynamin tracks, where x_pos is sometimes NaN
#         print('num nans', df.isna().sum())
        df['pid'] = np.arange(df.shape[0])  # assign each track a unique id
        df['valid'] = True  # all tracks start as valid
        if DSET['test'] is not None:
            df['valid'][df.cell_num.isin(DSET['test'])] = False
        metadata['num_tracks'] = df.valid.sum()

        print('\tpreprocessing data...')
        df = remove_invalid_tracks(df)  # use catIdx
        df = features.add_basic_features(df)
        df = outcomes.add_outcomes(df, LABELS=LABELS)

        metadata['num_tracks_valid'] = df.valid.sum()
        metadata['num_aux_pos_valid'] = df[df.valid][outcome_def].sum()
        metadata['num_hotspots_valid'] = df[df.valid]['hotspots'].sum()
        df['valid'][df.hotspots] = False
        df, meta_lifetime = process_tracks_by_lifetime(df, outcome_def=outcome_def,
                                                       plot=False, acc_thresh=acc_thresh,
                                                       previous_meta_file=previous_meta_file)
        df['valid'][df.short] = False
        df['valid'][df.long] = False
        metadata.update(meta_lifetime)
        metadata['num_tracks_hard'] = df['valid'].sum()
        metadata['num_aux_pos_hard'] = int(df[df.valid == 1][outcome_def].sum())

        print('\tadding features...')
#         df = df.replace([np.inf, -np.inf], np.nan)
#         df = df.fillna(df.median()) # this only does anything for the dynamin tracks, where some feats are NaN
#         df = df.fillna(0) # this only does anything for the dynamin tracks, where some feats are NaN
        # df = features.add_dict_features(df, use_processed=use_processed_dicts)
        # df = features.add_smoothed_tracks(df)
        # df = features.add_pcs(df)
        # df = features.add_trend_filtering(df) 
        df = features.add_binary_features(df, outcome_def=outcome_def)
        if save_processed:
            pkl.dump(metadata, open(metadata_file, 'wb'))
            df.to_pickle(processed_file)
    return df


def remove_invalid_tracks(df, keep=[1, 2]):
    '''Remove certain types of tracks based on cat_idx
    cat_idx (idx 1 and 2)
        1-4 (non-complex trajectory - no merges and splits)
            1 - valid
            2 - signal occasionally drops out
            3 - cut  - starts / ends
            4 - multiple - at the same place (continues throughout)
        5-8 (there is merging or splitting)
    '''
    df['lifetime_ref'] = [len(x) for x in df['X']]
    no_nan = df['lifetime'] == df['lifetime_ref']
    df = df[no_nan]
    return df[df.catIdx.isin(keep)]


def extract_X_mat(df):
    '''Extract matrix for X filled with zeros after sequences
    Width of matrix is length of longest lifetime
    '''
    p = df.lifetime.max()
    n = df.shape[0]
    X_mat = np.zeros((n, p)).astype(np.float32)
    X = df['X'].values
    for i in range(n):
        x = X[i]
        num_timepoints = min(p, len(x))
        X_mat[i, :num_timepoints] = x[:num_timepoints]
    X_mat = np.nan_to_num(X_mat)
    X_mat -= np.min(X_mat)
    X_mat /= np.std(X_mat)
    return X_mat


def process_tracks_by_lifetime(df: pd.DataFrame, outcome_def: str,
                               plot=False, acc_thresh=0.95, previous_meta_file=None):
    '''Calculate accuracy you can get by just predicting max class 
    as a func of lifetime and return points within proper lifetime (only looks at training cells)
    '''
    vals = df[df.valid == 1][['lifetime', outcome_def]]

    R, C = 1, 3
    lifetimes = np.unique(vals['lifetime'])

    # cumulative accuracy for different thresholds
    accs_cum_lower = np.array([1 - np.mean(vals[outcome_def][vals['lifetime'] <= l]) for l in lifetimes])
    accs_cum_higher = np.array([np.mean(vals[outcome_def][vals['lifetime'] >= l]) for l in lifetimes]).flatten()

    if previous_meta_file is None:
        try:
            idx_thresh = np.nonzero(accs_cum_lower >= acc_thresh)[0][-1]  # last nonzero index
            thresh_lower = lifetimes[idx_thresh]
        except:
            idx_thresh = 0
            thresh_lower = lifetimes[idx_thresh] - 1
        try:
            idx_thresh_2 = np.nonzero(accs_cum_higher >= acc_thresh)[0][0]
            thresh_higher = lifetimes[idx_thresh_2]
        except:
            idx_thresh_2 = lifetimes.size - 1
            thresh_higher = lifetimes[idx_thresh_2] + 1
    else:
        previous_meta = pkl.load(open(previous_meta_file, 'rb'))
        thresh_lower = previous_meta['thresh_short']
        thresh_higher = previous_meta['thresh_long']

    # only df with lifetimes in proper range
    df['short'] = df['lifetime'] <= thresh_lower
    df['long'] = df['lifetime'] >= thresh_higher
    n = vals.shape[0]
    n_short = np.sum(df['short'])
    n_long = np.sum(df['long'])
    acc_short = 1 - np.mean(vals[outcome_def][vals['lifetime'] <= thresh_lower])
    acc_long = np.mean(vals[outcome_def][vals['lifetime'] >= thresh_higher])

    metadata = {'num_short': n_short, 'num_long': n_long, 'acc_short': acc_short,
                'acc_long': acc_long, 'thresh_short': thresh_lower, 'thresh_long': thresh_higher}

    if plot:
        plt.figure(figsize=(12, 4), dpi=200)
        plt.subplot(R, C, 1)
        outcome = df[outcome_def]
        plt.hist(df['lifetime'][outcome == 1], label='aux+', alpha=1, color=cb, bins=25)
        plt.hist(df['lifetime'][outcome == 0], label='aux-', alpha=0.7, color=cr, bins=25)
        plt.xlabel('lifetime')
        plt.ylabel('count')
        plt.legend()

        plt.subplot(R, C, 2)
        plt.plot(lifetimes, accs_cum_lower, color=cr)
        #     plt.axvline(thresh_lower)
        plt.axvspan(0, thresh_lower, alpha=0.2, color=cr)
        plt.ylabel('fraction of negative events')
        plt.xlabel(f'lifetime <= value\nshaded includes {n_short / n * 100:0.0f}% of pts')

        plt.subplot(R, C, 3)
        plt.plot(lifetimes, accs_cum_higher, cb)
        plt.axvspan(thresh_higher, max(lifetimes), alpha=0.2, color=cb)
        plt.ylabel('fraction of positive events')
        plt.xlabel(f'lifetime >= value\nshaded includes {n_long / n * 100:0.0f}% of pts')
        plt.tight_layout()

    return df, metadata


def get_feature_names(df):
    '''Returns features (all of which are scalar)
    Removes metadata + time-series columns + outcomes
    '''
    ks = list(df.keys())
    feat_names = [
        k for k in ks
        if not k.startswith('y')
           and not k.startswith('Y')
           and not k.startswith('Z')
           and not k.startswith('pixel')
           #         and not k.startswith('pc_')
           and not k in ['catIdx', 'cell_num', 'pid', 'valid',  # metadata
                         'X', 'X_pvals', 'x_pos', 'X_starts', 'X_ends', 'X_extended',  # curves
                         'short', 'long', 'hotspots', 'sig_idxs',  # should be weeded out
                         'X_max_around_Y_peak', 'X_max_after_Y_peak',  # redudant with X_max / fall
                         'X_max_diff', 'X_peak_idx',  # unlikely to be useful
                         't', 'x_pos_seq', 'y_pos_seq',  # curves
                         'X_smooth_spl', 'X_smooth_spl_dx', 'X_smooth_spl_d2x'  # curves
                         ]
    ]
    return feat_names


def select_final_feats(feat_names, binarize=False):
    feat_names = [x for x in feat_names
                  if not x.startswith('sc_')
                  and not x.startswith('nmf_')
                  and not x in ['center_max', 'left_max', 'right_max', 'up_max', 'down_max',
                                'X_max_around_Y_peak', 'X_max_after_Y_peak', 'X_max_diff_after_Y_peak']
                  and not x.startswith('pc_')
                  and not 'extended' in x
                  #               and not 'X_peak' in x
                  #               and not 'slope' in x
                  #               and not x in ['fall_final', 'fall_slope', 'fall_imp', 'fall']
                  ]
    feat_names = [x for x in feat_names if not '_tf_smooth' in x]
    feat_names = [x for x in feat_names if not 'local' in x]
    feat_names = [x for x in feat_names if not 'last' in x]
    # feat_names = [x for x in feat_names if '_tf_smooth' in x]

    if binarize:
        feat_names = [x for x in feat_names if 'binary' in x]
    else:
        feat_names = [x for x in feat_names if not 'binary' in x]
    return feat_names


if __name__ == '__main__':
    
    # process original data (and save out lifetime thresholds)
    dset_orig = 'clath_aux+gak_a7d2'
    df = get_data(dset=dset_orig)  # save out orig
    
    # process new data (using lifetime thresholds from original data)
    outcome_def = 'y_consec_sig'
    for dset in ['clath_aux_dynamin']:
#     for dset in config.DSETS.keys():
        df = get_data(dset=dset,
                      previous_meta_file=f'{config.DIR_PROCESSED}/metadata_{dset_orig}.pkl')
        print(dset, 'num cells', len(df['cell_num'].unique()), 'num tracks', df.shape[0], 'num aux+',
              df[outcome_def].sum(), 'aux+ fraction', (df[outcome_def].sum() / df.shape[0]).round(3),
              'valid', df.valid.sum(), 'valid aux+', df[df.valid][outcome_def].sum(), 'valid aux+ fraction',
              (df[df.valid][outcome_def].sum() / df.valid.sum()).round(3))