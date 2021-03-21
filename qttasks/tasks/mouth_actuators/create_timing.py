from pathlib import Path
from numpy import mean
from numpy.random import shuffle, uniform

TASK_DIRECTORY = Path(__file__).resolve().parent

EVENTS = (
    'rest',
    'larynx',
    'lips',
    'teeth',
    'tongue'
    )
N_REPETITIONS = 15
BASELINE = 3
TRL_DUR = [5, 9]
STIM_ON = 3
CODE_OFFSET = 150

def main():
    timing_tsv = TASK_DIRECTORY / 'timing.tsv'

    total_dur = BASELINE + mean(TRL_DUR) * N_REPETITIONS * len(EVENTS)
    print(f'Total approx duration: {total_dur:0.3f} seconds')
    print(f'Total approx duration: {total_dur // 60:0.0f}\'{total_dur % 60:0.3f}"')

    events = list(EVENTS) * N_REPETITIONS
    shuffle(events)

    with timing_tsv.open('w') as f:
        f.write('onset\tduration\ttrial_name\tstim_file\ttrial_type\n')
        for i, evt in enumerate(events):
            if i == 0:
                onset = BASELINE
            else:
                onset += uniform(TRL_DUR[0], TRL_DUR[1])
            code = EVENTS.index(evt) + CODE_OFFSET
            f.write(f'{onset:0.3f}\t{STIM_ON}\t{evt}\timages/{evt}.png\t{code:.0f}\n')


if __name__ == '__main__':
    main()
