import threading as th
from pathlib import Path
import json

from utility import DotDict, tofloat


class Axis:
    def __init__(self, name, *, ax_label=None, save_column=None, ax_scale='linear'):
        """
        If things are None, they will not be used
        If things are 'True', the value of name will be used, with '_' replaced with ' '
        """
        self.name = name
        self.ax_label = name.replace('_', ' ') if ax_label == True else ax_label
        self.ax_scale = ax_scale
        self.save_column = name.replace(
                '_', ' ') if save_column == True else save_column
        self.data = []

    def reset(self):
        self.data.clear()


class AxisFileGroup:
    def __init__(self, file_path_prefix):
        self.lock = th.Lock()

        self.current_out_file = None
        self.file_counter = 0
        self.file_path_prefix = file_path_prefix
        self.file_user = ''
        self.file_sample = ''
        self.updated = False
        self.start_measurement = True

        self.axes = DotDict({})

        self.input = DotDict({})
        self.input.fname = None
        self.input.dat = None
        self.input.index = 1
        self.input.T_sensor = None  # from input file
        self.input.T_threshold = None  # from input file


        self.sample_thickness = None  # nm
        self.sample_other_resistance = None  # Ω


    def tryAddRowToTable(self):
        if not self.input.dat:
            return
        if all([a!=a for a in self.input.dat[-1].values()]):
            return
        self.input.dat.append(dict((k, float('nan'))
                                   for k in self.input.dat[0]))
        return True

    def openInputFile(self, fname):
        """ self.input.dat will be a list of dicts """
        with open(fname, 'r') as f:
            l = f.readline()
            if l[:8] != '#GPIBM_I':
                print(l[:7])
                raise ValueError('Invalid Input File')
            dic = json.loads(l[8:])
            cols = f.readline().strip('\r\n').split('\t')
            rows = []
            for l in f.readlines():
                if not (l:=l.strip('\r\n')):
                    break
                row = list(map(tofloat, l.split('\t')))
                if (diff:=len(cols)-len(row)) > 0:
                    row.extend([float('nan')]*diff)
                # rows.append(row)
                rows.append(dict(zip(cols,row)))
            # dat = dict(zip(cols, [list(a) for a in zip(*rows)]))
        self.input.clear()
        self.input.dat = rows
        self.input.update(dic)
        self.input.index = 1
        self.input.fname = fname
        self.tryAddRowToTable()

    def writeInputFile(self, fname):
        with open(fname, 'w') as f:
            f.write('#GPIBM_I '+f'{{"T_sensor": "{self.input.T_sensor}", '+
                     f'"T_threshold": {self.input.T_threshold} }}\n')
            f.write('\t'.join(self.input.dat[0].keys())+'\n')
            for i, l in enumerate(self.input.dat):
                if float('nan') in (vs:=l.values()) and i > 0:
                    break
                f.write('\t'.join(map(str, vs))+'\n') 
        self.input_fname = fname

        
    def closeOutputFile(self):
        if (f := self.current_out_file):
            self.current_out_file = None
            f.close()
            return f.closed
        return None
        
    def openOutputFile(self):
        self.closeOutputFile()
        path = (Path(self.file_path_prefix) / self.file_user /
                self.file_sample /
                f'{self.file_sample}-{self.date_start}_{self.file_counter:2d}.txt'
                ).resolve()
        path.parent.mkdir(exist_ok=True, parents=True)
        self.current_out_file = open(path, 'a')
        # write column headers
        self.current_out_file.write('\t'.join([
            f"'{ax.save_column}'" for ax in self.axes.values() if ax.save_column
            ])+'\n')

    
    def writeOutputLine(self):
        if not self.current_out_file:
            self.openOutputFile()

        self.current_out_file.write('\t'.join([
            str(ax.data[-1] if len(ax.data)>=1 else None) for ax in self.axes.values() if ax.save_column
            ])+'\n')


        
