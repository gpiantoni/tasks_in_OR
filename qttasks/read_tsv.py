from numpy import (
    append,
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
        if n in ('onset', 'duration'):
            dtypes.append((n, '<f8'))  # make sure they are float
        elif tsv.dtype[n].kind == 'U':
            dtypes.append((n, 'U4096'))
        else:
            dtypes.append((n, tsv.dtype[n]))

    tsv = array(tsv, dtype=dtype(dtypes))

    x = empty((1, ), dtype=tsv.dtype)
    x['onset'] = 0
    x['duration'] = 0.5  # should be parameter
    x['stim_file'] = 'task start'
    x['trial_type'] = 250
    tsv = insert(tsv, 0, x)

    x = empty((1, ), dtype=tsv.dtype)
    x['onset'] = tsv['onset'][-1] + tsv['duration'][-1] + P['OUTRO']
    x['duration'] = 0.5  # should be parameter
    x['stim_file'] = 'task end'
    x['trial_type'] = 251
    tsv = append(tsv, x)

    out_tsv = []
    for i in range(tsv.shape[0] - 1):
        out_tsv.append(tsv[i:i + 1])
        end_image = tsv[i]['onset'] + tsv[i]['duration']
        next_image = tsv[i + 1]['onset']

        if end_image < next_image:
            x = empty((1, ), dtype=tsv.dtype)
            x['onset'] = end_image
            x['stim_file'] = P['BASELINE']
            x['trial_type'] = 0
            out_tsv.append(x)
    out_tsv.append(tsv[-1:])
    tsv = squeeze(array(out_tsv))

    d_images = {}
    for img in set(tsv['stim_file']):
        if img.endswith('.png') or img.endswith('.jpg'):
            img_file = IMAGES_DIR / img
            if not img_file.exists():
                print(f'{img_file} does not exist')
            d_images[img] = QPixmap(str(img_file))

    # change dtype for stim_file only
    dtypes = []
    for k, v in tsv.dtype.descr:
        if k == 'stim_file':
            v = 'O'
        dtypes.append((k, v))
    tsv = tsv.astype(dtypes)
    
    for i in range(tsv['stim_file'].shape[0]):
        if tsv['stim_file'][i].endswith('.png') or tsv['stim_file'][i].endswith('.jpg'):
            tsv['stim_file'][i] = d_images[tsv['stim_file'][i]]

    return tsv