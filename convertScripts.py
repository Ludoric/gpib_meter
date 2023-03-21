import pandas as pd

fin = '/storage/Ted-REN_Data/samples/CCC_data/Sequences/Basic2.seq'
fout = '/storage/Ted-REN_Data/samples/CCC_data/Sequences/Basic2.pyseq'

ind = pd.read_csv(fin, sep='\t')
print(ind)
outd = ind[['current', 'temp1', 'time', 'ramp rate']]
outd = outd.rename(columns={'current': 'I_start', 'temp1': 'T_end', 'time': 'time_dwell', 'ramp rate': 'T_ramp_rate'})
outd['I_end'] = outd['I_start'].copy()
outd['time_dwell'] *= 60
outd['T_end'].replace(0, method='ffill', inplace=True)


outd['V_limit'] = 15.0
outd['time_datapoint'] = 60

outd = outd[['I_start', 'I_end', 'T_end', 'T_ramp_rate', 'time_dwell', 'V_limit', 'time_datapoint']]


outd.to_csv(fout, index=False, sep='\t')
print(outd)
