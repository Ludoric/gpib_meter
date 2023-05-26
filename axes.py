import threading as th
from pathlib import Path
from datetime import datetime
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

class Input:
    def __init__(self):
        self.fname = None
        self.dat = None
        self.index = 0

        self.magicNumber = {}
        # only here so you know what to expect
        # (not enforeced, but will crash if missing)
        self.magicNumber['T_sensor'] = None  # from input file
        self.magicNumber['T_threshold'] = None  # from input file
        self.magicNumber['time_giveup'] = None  # from input file

    def addRowToTable(self):
        if not self.dat:
            return
        nl = self.dat[self.index].copy() if self.index >= 0 else (
                dict((k, float('nan')) for k in self.dat[0]))
        self.dat.insert(self.index, nl)
        return True
    
    def removeRowFromTable(self):
        if not self.dat:
            return
        if self.index >= len(self.dat):
            return
        del self.dat[self.index]
        if self.index == len(self.dat):
            self.index -= 1
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
        self.magicNumber.clear()
        self.magicNumber.update(dic)
        self.dat = rows
        self.index = 0
        self.fname = fname

    def writeInputFile(self, fname):
        with open(fname, 'w') as f:
            f.write('#GPIBM_I '+json.dumps(self.magicNumber)+'\n')
            f.write('\t'.join(self.dat[0].keys())+'\n')
            for i, l in enumerate(self.dat):
#                 if float('nan') in (vs:=l.values()) and i > 0:
#                     break
                f.write('\t'.join(map(str, l.values()))+'\n') 
        self.input_fname = fname


class AxisFileGroup:
    def __init__(self, file_path_prefix):
        self.lock = th.Lock()

        self.current_out_file = None
        self.file_counter = 0
        self.file_path_prefix = file_path_prefix
        self.file_user = ''
        self.file_sample = ''
        self.updated = False # used to check when to update the plot
        self.force_next_input_line = True # used to request a new output file

        self.axes = DotDict({})

        self.input = Input()

        # unused: (to delete?)
        self.sample_thickness = None  # nm
        self.sample_other_resistance = None  # Ω

    def prepareForMeasurement(self):
        self.date_start = datetime.today().strftime('%d_%m_%Y')
        [a.reset() for a in self.axes.values()]
        if not self.file_path_prefix:
            raise ValueError('Please enter a file path prefix')
        if not self.file_user:
            raise ValueError('Please enter a user')
        if not self.file_sample:
            raise ValueError('Please enter a sample ID')
        if  0 > self.input.index or self.input.index >= len(self.input.dat):
            raise ValueError('Invalid starting line: Please select a starting line')
        self.file_counter = 0
        self.openOutputFile()
        
    def closeOutputFile(self):
        if (f := self.current_out_file):
            self.current_out_file = None
            f.close()
            return f.closed
        return None
        
    def openOutputFile(self):
        self.closeOutputFile()
        self.file_counter += 1
        path = (Path(self.file_path_prefix) / self.file_user /
                self.file_sample /
                f'{self.file_sample}-{self.date_start}_{self.file_counter:2d}.txt'
                ).resolve()
        path.parent.mkdir(exist_ok=True, parents=True)
        self.current_out_file = open(path, 'a')
        # write column headers
        self.current_out_file.write('\t'.join([
            f"'{ax.save_column}'"
            for ax in self.axes.values() if ax.save_column
            ])+'\n')

    
    def writeOutputLine(self):
        if not self.current_out_file:
            self.openOutputFile()
        self.current_out_file.write('\t'.join([
            str(ax.data[-1] if len(ax.data)>=1 else None)
            for ax in self.axes.values() if ax.save_column
            ])+'\n')


        
