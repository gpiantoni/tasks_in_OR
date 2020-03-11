
def read_stimuli(P):

    STIMULI_TSV = str(IMAGES_DIR / P['TASK_TSV'])
    
    tsv = genfromtxt(
        fname=STIMULI_TSV,
        delimiter='\t',
        names=True,
        dtype=None,  # forces it to read strings
        deletechars='',
        encoding='utf-8')

    new_dtypes = []
    for n in dtypes.names:
        if dtypes[n].kind == 'U':
            new_dtypes.append((n, 'U4096'))
        else:
            new_dtypes.append((n, dtypes[n]))
            
    tsv = array(tsv, dtype= dtype(new_dtypes))


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
        out_tsv.append(tsv[i:i+1])
        end_image = tsv[i]['onset'] + tsv[i]['duration']
        next_image = tsv[i + 1]['onset']

        if end_image < next_image:
            x = empty((1, ), dtype=tsv.dtype)
            x['onset'] = end_image
            x['trial_name'] = P['BASELINE']
            x['trial_type'] = 0
            out_tsv.append(x)
    tsv = squeeze(array(out_tsv))   
    
    d_images = {png: QtGui.QPixmap(str(IMAGES_DIR / png)) for png in set(tsv['stim_file']) if png.endswith('.png') or png.endswith('.jpg')}
    
    stim_file = tsv['stim_file'].astype('O')
    for i in range(stim_file.shape[0]):
        if stim_file[i] == '':
            stim_file[i] = None
        elif stim_file[i].endswith('.png') or stim_file[i].endswith('.jpg'):
            stim_file[i] = d_images[stim_file[i]]
            
    tsv['stim_file'] = stim_file
    return tsv