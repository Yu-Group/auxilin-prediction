import pickle as pkl
import sys
sys.path.append('..')
import config
import data
from os.path import join as oj
import matplotlib.gridspec as grd
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib_venn import venn2
from sklearn import decomposition
from sklearn import metrics
from sklearn.covariance import EllipticEnvelope
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.utils.multiclass import unique_labels
import os
import matplotlib.ticker as mtick
from config import DIR_FIGS
from matplotlib.colors import LinearSegmentedColormap
# DIR_FILE = os.path.dirname(os.path.realpath(__file__)) # directory of this file
# DIR_FIGS = oj(DIR_FILE, '../reports/figs')


cb2 = '#66ccff'
cb = '#1f77b4'
co = '#ff7f0e'
cr = '#cc0000'
cp = '#cc3399'
cy = '#d8b365'
cg = '#5ab4ac'
cmap = LinearSegmentedColormap.from_list(
    name='orange-blue', 
    colors=[(205/255, 85/255, 51/255),
            'lightgray',
            (50/255, 129/255, 168/255)]
)

def savefig(s: str, png=False):
#     plt.tight_layout()
    plt.savefig(oj(DIR_FIGS, 'fig_' + s + '.pdf'), bbox_inches='tight')
    if png:
        plt.savefig(oj(DIR_FIGS, 'fig_' + s + '.png'), dpi=300, bbox_inches='tight')
    

def fix_feat_name(s):
    return s.replace('_', ' ').replace('X', 'Clath').capitalize()

def plot_confusion_matrix(y_true, y_pred, classes,
                          normalize=False,
                          title=None,
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    Params
    ------
    classes: np.ndarray(Str)
        classes=np.array(['aux-', 'aux+'])
    """
    plt.figure(dpi=300)
    if not title:
        if normalize:
            title = 'Normalized confusion matrix'
        else:
            title = 'Confusion matrix, without normalization'

    # Compute confusion matrix
    cm = metrics.confusion_matrix(y_true, y_pred)
    # Only use the labels that appear in the data
    classes = classes[unique_labels(y_true.astype(np.int), y_pred.astype(np.int))]
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    #     fig, ax = plt.subplots()
    im = plt.imshow(cm, interpolation='nearest', cmap=cmap)
    ax = plt.gca()
    #     ax.figure.colorbar(im, ax=ax)
    # We want to show all ticks...
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           # ... and label them with the respective list entries
           xticklabels=classes, yticklabels=classes,
           #            title=title,
           ylabel='True label',
           xlabel='Predicted label')

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right",
             rotation_mode="anchor")

    # Loop over data dimensions and create text annotations.
    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], fmt),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black")
    return ax


def highlight_max(data, color='#0e5c99'):
    '''
    highlight the maximum in a Series or DataFrame
    '''
    attr = 'background-color: {}'.format(color)
    if data.ndim == 1:  # Series from .apply(axis=0) or axis=1
        is_max = data == data.max()
        return [attr if v else '' for v in is_max]
    else:  # from .apply(axis=None)
        is_max = data == data.max().max()
        return pd.DataFrame(np.where(is_max, attr, ''),
                            index=data.index, columns=data.columns)


# visualize biggest errs
def viz_biggest_errs(df, idxs_cv, idxs, Y_test, preds, preds_proba,
                     num_to_plot=20,
                     aux_thresh=642,
                     show_track_num=True,
                     show_track_pid=False,
                     sort_by_residuals=True,
                     plot_x=True,
                     plot_y=True,
                     plot_z=False,
                     xlim_constant=True,
                     lifetime_max=None,
                     text_labels=False):
    '''Visualize X and Y where the top examples are the most wrong / least confident
    Params
    ------
    idxs_cv: integer ndarray
        which idxs are not part of the test set (usually just 0, 1, 2, ...)
    idxs: boolean ndarray
        subset of points to plot
    
    '''

    
    # deal with idxs
    if idxs is not None:
        Y_test = Y_test[idxs]
        preds = preds[idxs]
        preds_proba = preds_proba[idxs]
        if idxs_cv is None:
            idxs_cv = np.arange(df.shape[0])
        df = df.iloc[idxs_cv][idxs]
    
    # get args to sort by
    if sort_by_residuals:
        residuals = np.abs(Y_test - preds_proba)
        args = np.argsort(residuals)[::-1]
        dft = df.iloc[args]
    else:
        dft = df
    if lifetime_max is None:
        lifetime_max = np.max(dft.lifetime.values)
    if num_to_plot is None:
        num_to_plot = dft.shape[0]
    R = int(np.sqrt(num_to_plot))
    C = num_to_plot // R  # + 1
    plt.figure(figsize=(C * 3, R * 2.5), dpi=200)

    i = 0
    for r in range(R):
        for c in range(C):
            if i < dft.shape[0]:
                row = dft.iloc[i]
                ax = plt.subplot(R, C, i + 1)
                # show nums on tracks
                if show_track_num:
                    ax.text(.5, .9, f'{i}', # row.pid
                            horizontalalignment='right',
                            transform=ax.transAxes)
                elif show_track_pid:
                    ax.text(.5, .9, f'{row.pid}', # row.pid
                            horizontalalignment='right',
                            transform=ax.transAxes)
                plt.axis('off')
                
                if plot_x:
                    plt.plot(row["X"], color=cr, label='clath', lw=2) # could do X_extended
                if plot_y:
                    plt.plot(row["Y"], color=cg, label='aux', lw=2)
                if plot_z:
                    plt.plot(row["Z"], color='gray', label='dyn')

                if xlim_constant:
                    plt.xlim([-1, lifetime_max])
                plt.axhline(aux_thresh, color='gray', alpha=0.5, lw=2)
                i += 1
                
    if text_labels:
        plt.text(len(row["X"]), row["X"][-1], 'Clathrin', color=cr, fontsize=25, fontweight='bold')
        plt.text(len(row["Y"]), row["Y"][-1], 'Auxilin', color=cg, fontsize=25, fontweight='bold')
        if plot_z:
            plt.text(len(row["Z"]), row["Z"][-1], 'Dynamin', color='gray', fontsize=25, fontweight='bold')
    plt.tight_layout()
    return dft


def viz_errs_2d(df, idxs_test, preds, Y_test, key1='x_pos', key2='y_pos', X=None, plot_correct=True):
    '''visualize distribution of errs wrt to 2 dimensions
    '''
    x_pos = df[key1].iloc[idxs_test]
    y_pos = df[key2].iloc[idxs_test]

    plt.figure(dpi=200)
    ms = 4
    me = 1
    if plot_correct:
        plt.plot(x_pos[(preds == Y_test) & (preds == 1)], y_pos[(preds == Y_test) & (preds == 1)], 'o',
                 color=cb, alpha=0.4, label='true pos', ms=ms, markeredgewidth=0)
        plt.plot(x_pos[(preds == Y_test) & (preds == 0)], y_pos[(preds == Y_test) & (preds == 0)], 'o',
                 color=cr, alpha=0.4, label='true neg', ms=ms, markeredgewidth=0)
    plt.plot(x_pos[preds > Y_test], y_pos[preds > Y_test], 'x', color=cb,
             alpha=0.4, label='false pos', ms=ms, markeredgewidth=1)
    plt.plot(x_pos[preds < Y_test], y_pos[preds < Y_test], 'x', color=cr,
             alpha=0.4, label='false neg', ms=ms, markeredgewidth=1)
    plt.legend()
    #     plt.scatter(x_pos, y_pos, c=preds==Y_test, alpha=0.5)
    plt.xlabel(key1)
    plt.ylabel(key2)
    plt.tight_layout()


def viz_errs_1d(X_test, preds, preds_proba, Y_test, norms, key='lifetime'):
    '''visualize errs based on lifetime
    '''
    plt.figure(dpi=200)
    correct_idxs = preds == Y_test
    lifetime = X_test[key] * norms[key]['std'] + norms[key]['mu']

    plt.plot(lifetime[(preds == Y_test) & (preds == 1)], preds_proba[(preds == Y_test) & (preds == 1)], 'o',
             color=cb, alpha=0.5, label='true pos')
    plt.plot(lifetime[(preds == Y_test) & (preds == 0)], preds_proba[(preds == Y_test) & (preds == 0)], 'x',
             color=cb, alpha=0.5, label='true neg')
    plt.plot(lifetime[preds > Y_test], preds_proba[preds > Y_test], 'o', color=cr, alpha=0.5, label='false pos')
    plt.plot(lifetime[preds < Y_test], preds_proba[preds < Y_test], 'x', color=cr, alpha=0.5, label='false neg')
    plt.xlabel(key)
    plt.ylabel('predicted probability')
    plt.legend()
    plt.show()


def plot_curves(df, extra_key=None, extra_key_label=None,
                hline=True, R=5, C=8,
                fig=None, ylim_constant=False, xlim_constant=True, legend=True, plot_x=True):
    '''Plot time-series curves from df
    '''
    if fig is None:
        plt.figure(figsize=(16, 10), dpi=200, facecolor='white')
    lifetime_max = np.max(df.lifetime.values[:R * C])
    df = df.iloc[range(R * C)]
    for i in range(R * C):
        if i < df.shape[0]:
            plt.subplot(R, C, i + 1)
            row = df.iloc[i]
            if plot_x:
                plt.plot(row.X, color=cr, label='Clathrin')
                plt.plot(row.Y, color=cg, label='Auxilin')
                if hline:
                    plt.axhline(642.3754691658837, color='gray', alpha=0.5)
            if extra_key is not None:
                if extra_key_label is None:
                    if extra_key == 'Z':
                        extra_key_label = 'Dynamin'
                    else:
                        extra_key_label = extra_key
                plt.plot(row[extra_key], color='gray', label=extra_key_label)
            if xlim_constant:
                plt.xlim([-1, lifetime_max + 1])
            if ylim_constant:
                plt.ylim([-10, max(max(df.X_max), max(df.Y_max)) + 1])
    #     plt.axi('off')
    if legend:
        plt.legend()
    plt.tight_layout()
    if fig is None:
        plt.show()


def viz_errs_outliers_venn(X_test, preds, Y_test, num_feats_reduced=5):
    '''Compare outliers to errors in venn-diagram
    '''
    feat_names = data.get_feature_names(X_test)
    X_feat = X_test[feat_names]

    if num_feats_reduced is not None:
        pca = decomposition.PCA(n_components=num_feats_reduced)
        X_reduced = pca.fit_transform(X_feat)
    else:
        X_reduced = X_feat

    R, C = 2, 2
    titles = ['isolation forest', 'local outlier factor', 'elliptic envelop', 'one-class svm']
    plt.figure(figsize=(6, 5), dpi=200)
    for i in range(4):
        plt.subplot(R, C, i + 1)
        plt.title(titles[i])
        if i == 0:
            clf = IsolationForest(n_estimators=10, warm_start=True)
        elif i == 1:
            clf = LocalOutlierFactor(novelty=True)
        elif i == 2:
            clf = EllipticEnvelope()
        elif i == 3:
            clf = OneClassSVM()
        clf.fit(X_reduced)  # fit 10 trees  
        is_outlier = clf.predict(X_reduced) == -1
        is_err = preds != Y_test
        idxs = np.arange(is_outlier.size)
        venn2([set(idxs[is_outlier]), set(idxs[is_err])], set_labels=['outliers', 'errors'])


def plot_pcs(pca, X):
    '''Pretty plot of pcs with explained var bars
    Params
    ------
    pca: sklearn PCA class after being fitted
    '''
    plt.figure(figsize=(6, 9), dpi=200)

    # extract out relevant pars
    comps = pca.components_.transpose()
    var_norm = pca.explained_variance_ / np.sum(pca.explained_variance_) * 100

    # create a 2 X 2 grid 
    gs = grd.GridSpec(2, 2, height_ratios=[2, 10],
                      width_ratios=[12, 1], wspace=0.1, hspace=0)

    # plot explained variance
    ax2 = plt.subplot(gs[0])
    ax2.bar(np.arange(0, comps.shape[1]), var_norm,
            color='gray', width=0.8)
    plt.title('Explained variance (%)')
    ax2.spines['right'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax2.yaxis.set_ticks_position('left')
    ax2.set_yticks([0, max(var_norm)])
    plt.xlim((-0.5, comps.shape[1] - 0.5))

    # plot pcs
    ax = plt.subplot(gs[2])
    vmaxabs = np.max(np.abs(comps))
    p = ax.imshow(comps, interpolation='None', aspect='auto',
                  cmap=sns.diverging_palette(10, 240, as_cmap=True, center='light'),
                  vmin=-vmaxabs, vmax=vmaxabs)  # center at 0
    plt.xlabel('PCA component number')
    ax.set_yticklabels(list(X))
    ax.set_yticks(range(len(list(X))))

    # make colorbar
    colorAx = plt.subplot(gs[3])
    cb = plt.colorbar(p, cax=colorAx)
    plt.show()


def print_metadata(acc=None, metadata_file=oj(config.DIR_PROCESSED, 'metadata_clath_aux+gak_a7d2.pkl')):
    m = pkl.load(open(metadata_file, 'rb'))

    print(
        f'valid:\t\t{m["num_aux_pos_valid"]:>4.0f} aux+ / {m["num_tracks_valid"]:>4.0f} ({m["num_aux_pos_valid"] / m["num_tracks_valid"]:.3f})')
    print('----------------------------------------')
    print(f'hotspots:\t{m["num_hotspots_valid"]:>4.0f} aux+ / {m["num_hotspots_valid"]:>4.0f}')
    print(
        f'short:\t\t{m["num_short"] - m["num_short"] * m["acc_short"]:>4.0f} aux+ / {m["num_short"]:>4.0f} ({m["acc_short"]:.3f})')
    print(f'long:\t\t{m["num_long"] * m["acc_long"]:>4.0f} aux+ / {m["num_long"]:>4.0f} ({m["acc_long"]:.3f})')
    print(
        f'hard:\t\t{m["num_aux_pos_hard"]:>4.0f} aux+ / {m["num_tracks_hard"]:>4.0f} ({m["num_aux_pos_hard"] / m["num_tracks_hard"]:.3f})')

    if acc is not None:
        print('----------------------------------------')
        print(f'hard acc:\t\t\t  {acc:.3f}')
        num_eval = m["num_tracks_valid"] - m["num_hotspots_valid"]
    #         print(
    #             f'total acc (no hotspots):\t  {(m["num_short"] * m["acc_short"] + m["num_long"] * m["acc_long"] + acc * m["num_tracks_hard"]) / num_eval:.3f}')
    print('\nlifetime threshes', m['thresh_short'], m['thresh_long'])


def jointplot_grouped(col_x: str, col_y: str, col_k: str, df,
                      k_is_color=False, scatter_alpha=.5, add_global_hists: bool = False, ms=None):
    '''Jointplot of hists + densities
    Params
    ------
    col_x
        name of X var
    col_y
        name of Y var
    col_k
        name of variable to group/color by
    add_global_hists
        whether to plot the global hist as well
    '''

    def colored_scatter(x, y, c=None):
        def scatter(*args, **kwargs):
            args = (x, y)
            if c is not None:
                kwargs['c'] = c
            kwargs['marker'] = '.'
            kwargs['alpha'] = scatter_alpha
            plt.scatter(*args, **kwargs)

        return scatter

    g = sns.JointGrid(
        x=col_x,
        y=col_y,
        data=df
    )
    color = None
    legends = []
    for name, df_group in df.groupby(col_k):
        legends.append(name)
        if k_is_color:
            color = name
        g.plot_joint(
            colored_scatter(df_group[col_x], df_group[col_y], color),
        )
        sns.distplot(
            df_group[col_x].values,
            ax=g.ax_marg_x,
            color=color,
        )
        sns.distplot(
            df_group[col_y].values,
            ax=g.ax_marg_y,
            color=color,
            vertical=True
        )
    if add_global_hists:
        sns.distplot(
            df[col_x].values,
            ax=g.ax_marg_x,
            color='grey'
        )
        sns.distplot(
            df[col_y].values.ravel(),
            ax=g.ax_marg_y,
            color='grey',
            vertical=True
        )
    plt.legend(legends)


# 2d decision boundary
def plot_decision_boundary(X_col, Y_col, m, df, norms, num_pts=100):
    '''still not finished...
    '''
    x = df[X_col]
    y = df[Y_col]
    x = np.linspace(x.min(), x.max(), num_pts)
    y = np.linspace(y.min(), y.max(), num_pts)

    # normalize
    xv, yv = np.meshgrid(x, y, indexing='ij')
    x = xv.flatten()
    y = yv.flatten()
    x = (x - norms[X_col]['mu']) / (norms[X_col]['std'])
    y = (y - norms[Y_col]['mu']) / (norms[Y_col]['std'])

    X = np.hstack((x, y)).reshape(-1, 2)
    print(X.shape)

    X = df[results_individual['feat_names_selected']]

    preds = m.predict(X)


def cumulative_acc_plot_hard(preds_proba, preds, y_full_cv):
    args = np.argsort(np.abs(preds_proba - 0.5))[::-1]
    accs = (preds == y_full_cv)[args]
    n = accs.size
    accs = np.cumsum(accs) / np.arange(1, n + 1)

    plt.figure(dpi=500)
    plt.plot(preds_proba[args], '.', ms=0.5, label='predicted prob', color=cb)
    plt.plot(accs, label='cumulative acc', color=cr)
    plt.yticks(np.arange(-0.05, 1.05, 0.1))
    plt.xlabel('num pts included')
    plt.grid(alpha=0.2)
    plt.legend()
    plt.show()


def cumulative_acc_plot_all(df, pred_proba_key='preds_proba', pred_key='preds',
                            outcome_def='y_consec_thresh',
                            plot_vert_line_for_high_lifetimes=False, show=True):
    plt.figure(dpi=500)
    ax = plt.subplot(111)
    
    # full (no model)
    argsf = np.argsort(df.lifetime.values)
    accsf = (1 - df[outcome_def]).values[argsf]
    n = df.shape[0]
    plt.plot(np.cumsum(accsf) / np.arange(1, accsf.size + 1), label='No model', color='gray')
    print('accsf', np.sum(accsf))
    
    # short
    ds = df[df.short]
    argss = np.argsort(ds.lifetime.values)
    accss = (1 - ds[outcome_def]).values[argss]
    ns = ds.shape[0]
    # hard
    dh = df[~df.short]
    argsh = np.argsort(np.abs(dh[pred_key])) #[::-1]
    accsh = ((dh[pred_key].values > 0) == dh[outcome_def].values)[argsh]
    # put things together
    accs = np.hstack((accss, accsh))
    print(accsf.shape, accss.shape, accsh.shape, accs.shape)
    plt.plot(np.cumsum(accs) / np.arange(1, accs.size + 1), label='With model', color=cb)
    print(accs)
    plt.axvline(ns, lw=2.5, color='black')
    
    
    plt.xlabel('Percentage of tracks included (sorted by uncertainty)')
    plt.ylabel('Accuracy')
    ax.xaxis.set_ticks([int(x) for x in np.arange(0, n + 1, n//5)])
    ax.xaxis.set_ticklabels([str(int(x)) + '%' for x in np.arange(0, 101, 100/5)])
    plt.legend(fontsize='x-large', frameon=False)
    plt.grid(alpha=0.2)
    plt.tight_layout()

def plot_example(ex):
    '''ex - row of the dataframe
    '''
    plt.figure(dpi=200)
    plt.plot(ex['X'], color='red', label='clathrin')
    plt.plot(ex['Y'], color='green', label='auxilin')
    plt.xlabel('Time')
    plt.ylabel('Amplitude')
    plt.legend()
