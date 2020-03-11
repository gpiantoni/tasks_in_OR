from numpy import (
    array,
    dtype,
    empty,
    genfromtxt,
    insert,
    squeeze,
    )
from PyQt5.QtGui import QPixmap

from .paths import IMAGES_DIR


def read_stimuli(P):

    STIMULI_TSV = str(IMAGES_DIR / P['TASK_TSV'])

    tsv = genfromtxt(
        fname=STIMULI_TSV,
        delimiter='\t',
        names=True,
        dtype=None,  # forces it to read strings
        deletechars='',
        encoding='utf-8')

    # make sure that that text are long enough to keep many chars
    dtypes = []
    for n in tsv.dtype.names:
        if tsv.dtype[n].kind == 'U':
            dtypes.append((n, 'U4096'))
        else:
            dtypes.append((n, tsv.dtype[n]))

    tsv = array(tsv, dtype=dtype(dtypes))

    x = empty((1, ), dtype=tsv.dtype)
    x['onset'] = 0
    x['duration'] = 0.5  # should be parameter
    x['trial_name'] = 'task start'
    x['trial_type'] = 250
    tsv = insert(tsv, 0, x)

    x = empty((1, ), dtype=tsv.dtype)
    x['onset'] = tsv['onset'][-1] + tsv['duration'][-1] + P['OUTRO']
    x['duration'] = 0.5  # should be parameter
    x['trial_name'] = 'task end'
    x['trial_type'] = 251
    tsv = insert(tsv, -1, x)

    out_tsv = []
    for i in range(tsv.shape[0] - 1):
        out_tsv.append(tsv[i:i + 1])
        end_image = tsv[i]['onset'] + tsv[i]['duration']
        next_image = tsv[i + 1]['onset']

        if end_image < next_image:
            x = empty((1, ), dtype=tsv.dtype)
            x['onset'] = end_image
            x['trial_name'] = P['BASELINE']
            x['trial_type'] = 0
            out_tsv.append(x)
    tsv = squeeze(array(out_tsv))

    d_images = {png: QPixmap(str(IMAGES_DIR / png)) for png in set(tsv['stim_file']) if png.endswith('.png') or png.endswith('.jpg')}

    stim_file = tsv['stim_file'].astype('O')
    for i in range(stim_file.shape[0]):
        if stim_file[i] == '':
            stim_file[i] = None
        elif stim_file[i].endswith('.png') or stim_file[i].endswith('.jpg'):
            stim_file[i] = d_images[stim_file[i]]

    tsv['stim_file'] = stim_file
    return tsv
