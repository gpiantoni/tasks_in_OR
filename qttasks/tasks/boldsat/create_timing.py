from pandas import DataFrame
from numpy import array, repeat, linspace, concatenate
from numpy.random import shuffle
from pathlib import Path

DUR_ON = 6
DUR_OFF = 4
N_EVENTS = 15
LEVELS = array([3, 6, 9, 12])
DUR = 0.2
BASELINE = 2
BOLDSAT_DIRECTORY = Path(__file__).resolve().parent


def main():
    l_events = repeat(LEVELS, N_EVENTS)
    shuffle(l_events)

    onsets = []
    trial_names = []
    trial_types = []
    for i, n_events in enumerate(l_events):
        onset_trl = linspace(0, DUR_ON, n_events) + i * (DUR_ON + DUR_OFF) + BASELINE
        onsets.append(onset_trl)

        freq = (n_events - 1) / DUR_ON
        trl_name = f'BOLDSAT_{(n_events - 1) / DUR_ON:0.2f}Hz'

        trial_names.append(trl_name)
        trial_names.extend(['BOLDSAT', ] * (n_events - 1))

        trial_types.append(int(freq * 100))
        trial_types.extend([1, ] * (n_events - 1))

    df = {
        'onset': concatenate(onsets),
        'duration': DUR,
        'trial_name': trial_names,
        'trial_type': trial_types,
        'stim_file': '../hrf/images/green_circle.png',
        }

    df = DataFrame(df)
    df.to_csv(BOLDSAT_DIRECTORY / 'timing.tsv', sep='\t', index=False, float_format='%.3f')


if __name__ == '__main__':
    main()
