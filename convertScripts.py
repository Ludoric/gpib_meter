import pandas as pd
from pathlib import Path
import sys

"""
I wrote this script in about 5min, so it is neither complicated nor professional
Example of use:

    python3 convertScript.py /path/to/your/sequence/file.seq

"""

if len(sys.argv) < 2:
    print('Please give the path to the file to be converted as an argument')
fin = Path(sys.argv[1])
fout = fin.with_suffix('.pyseq')


ind = pd.read_csv(fin, sep='\t')
outd = ind[['current', 'temp1', 'time', 'ramp rate']]
outd = outd.rename(columns={'current': 'I_start', 'temp1': 'T_end', 'time': 'time_max', 'ramp rate': 'T_ramp_rate'})
outd['I_end'] = outd['I_start'].copy()
outd['time_max'] *= 60
outd['T_end'].replace(0, method='ffill', inplace=True)

outd['V_limit'] = 15.0
outd['time_datapoint'] = 30

outd = outd[['I_start', 'I_end', 'V_limit', 'T_end', 'T_ramp_rate', 'time_max', 'time_datapoint']]

with open(fout, 'w') as f:
    f.write('#GPIBM_I {"T_sensor": "Temperature_B", "T_threshold": 0.1, "time_giveup": 3600}\n')
    outd.to_csv(f, index=False, sep='\t')

