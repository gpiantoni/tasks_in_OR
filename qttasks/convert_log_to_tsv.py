#!/usr/bin/env python3

from re import match
from datetime import datetime
from numpy import where, abs
from pandas import DataFrame
from argparse import ArgumentParser
from pathlib import Path


EPSILON = 0.010  # in ms


def import_txt(log_txt):

    df = {
        'time': [],
        'info': [],
        }

    with open(log_txt) as f:
        for line in f:
            g = match(r"(\d{2}:\d{2}:\d{2}.\d{3})\tqttask\t\w*\t(.*)", line)
            if g and (g.group(2).startswith('Sending trigger ') or g.group(2).startswith('Presenting ')):
                df['time'].append(datetime.strptime(g.group(1), '%H:%M:%S.%f'))
                df['info'].append(g.group(2))

    return DataFrame(df)


def reset_timing(df):
    i_trigger_start = where(df['info'] == 'Sending trigger 250')[0][0]
    t = df['time'] - df['time'][i_trigger_start]
    df['time'] = t.dt.total_seconds()
    return df

def split_database(df):
    """Split the database in triggers and events"""
    i_trigger = df['info'].str.startswith('Sending trigger ')
    i_present = df['info'].str.startswith('Presenting ')
    df_trg = df.loc[i_trigger]

    df_events = df.loc[i_present]
    idx_events = ~df_events['info'].isin(('Presenting BASELINE', 'Presenting '))
    df_events = df_events[idx_events]

    return df_trg, df_events


def create_tsv(df_trg):
    out = {
        'onset': [],
        'duration': [],
        'value': [],
        }

    needs_duration = False
    for row in df_trg.itertuples():
        trigger = row.info[16:]

        if trigger == '000':
            out['duration'].append(row.time - out['onset'][-1])
            needs_duration = False

        else:
            if needs_duration:
                out['duration'].append(0)

            out['onset'].append(row.time)
            out['value'].append(trigger)
            needs_duration = True

    if needs_duration:
        out['duration'].append(0)

    out = DataFrame(out)
    out['trial_name'] = ''
    return out


def assign_events_to_tsv(out, df_events):
    for row in df_events.itertuples():

        d = out.onset - row.time
        idx = abs(d).idxmin()

        if abs(out['onset'][idx] - row.time) <= EPSILON:
            out.loc[idx, 'trial_name'] = row.info[11:]
        else:
            print(f'Could not find matching trigger for event at {row.time}')

    return out


def convert_log_to_tsv(log_txt):
    df = import_txt(log_txt)
    df = reset_timing(df)
    df_trg, df_events = split_database(df)
    out = create_tsv(df_trg)
    out = assign_events_to_tsv(out, df_events)

    return out


def main():
    parser = ArgumentParser(prog='convert txt to tsv')
    parser.add_argument(
        'input',
        nargs='?',
        help='output of qttasks, with extension ".txt", to ".tsv"')
    args = parser.parse_args()

    log_txt = Path(args.input).resolve()
    tsv = convert_log_to_tsv(log_txt)

    out_tsv = log_txt.with_suffix('.tsv')
    assert not out_tsv.exists()
    tsv.to_csv(out_tsv, index=False, sep='\t', float_format='%.3f')
