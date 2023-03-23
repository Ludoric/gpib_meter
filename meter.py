from datetime import datetime
from pathlib import Path
import threading as th
import tkinter as tk
import traceback
import pyvisa
import ctypes
import time
import sys

from interface import Interface
from device import SimpleDevice
from utility import DotDict, printE
from axes import AxisFileGroup, Axis


class Meter:
    """
    This is a threaded program to allow the gui to be updated independently of
    the data collection.
    We launch the GUI from here, and must also close it from here
    The methods periodicCall and endApplication interface most directly with

    This is fairly terrible python code, and I apologise to anyone who has to read it
    """
    def __init__(self, root):
        """
        Main thread (this one) will be used by the interface.
        We create a new thread for the iteraction with the equipment
        """
        self.root = root
        

        self.measuring = False
        self.collectD_thread = th.Thread(target=self.collectData)
        self.collectD_thread.daemon = True


        self.axes = AxisFileGroup(r'C:\Cryostat\Cryostat\Data')
        # '/home/ludoric/Documents/PhD_stuff/GPIB_meter'
        self.axes.axes.Temperature_A = Axis(
                'Temperature_A', save_column=True, ax_label=True)
        self.axes.axes.Temperature_B = Axis(
                'Temperature_B', save_column=True, ax_label=True)
        self.axes.axes.Supply_Current = Axis(
                'Supply_Current', save_column='Desired Current', ax_label=True)
        self.axes.axes.Supply_Voltage = Axis(
                'Supply_Voltage', save_column=True, ax_label=True)
        self.axes.axes.Supply_Time = Axis(
                'Supply_Time', save_column=True, ax_label=True)
        self.axes.axes.Overcompliance = Axis(
                'Overcompliance', save_column=True)
        self.axes.axes.Pos_Current = Axis(
                'Pos_Current', save_column=True, ax_label=True)
        self.axes.axes.Neg_Current = Axis(
                'Neg_Current', save_column=True, ax_label=True)
        self.axes.axes.Pos_Voltage = Axis(
                'Pos_Voltage', save_column=True, ax_label=True)
        self.axes.axes.Neg_Voltage = Axis(
                'Neg_Voltage', save_column=True, ax_label=True)
        self.axes.axes.Voltage_Prefix = Axis(
                'Voltage_Prefix', save_column=True)
        self.axes.axes.Resistance = Axis(
                'Resistance', save_column='Resistance (From measured values)',
                ax_label=True, ax_scale='log')
        self.axes.axes.Resistivity = Axis(
                'Resistivity', save_column=True, ax_label=True, ax_scale='log')
        self.axes.axes.Time = Axis(
                'Time', save_column='Time (s)', ax_label=True)


        self.interface = Interface(
                root, self.stopApplication,
                self.startMeasurement, self.stopMeasurement,
                self.axes)
        self.interface.loadInputFile(file='./template.pyseq')


        self.running = True
        # start the periodic calls
        self.periodicCall()


    def startMeasurement(self):
        """
        Initialise the devices to read from and start the data collection thread
        """
        # try:
        self.initialiseDevices()
        # except Exception as e:
        #     printE('Error during instrument initialisation:\n' +
        #            f'{e}\nPlease check connections to instruments')
        # print(f"The ammeter is called {amps.device.query('*IDN?')}")
        # self.devices.volts.set('screen', 'POTATOES')
        # time.sleep(1)
        # self.devices.volts.set('screen_reset')
        # print([f'{x[0]}={x[1]}' for d in self.devices.items()
        #        for x in zip(d.titles, d.read())].join(', '))

        self.interface.update_axis_fields()
        self.axes.prepareForMeasurement()

        self.measuring = True
        self.collectD_thread = th.Thread(target=self.collectData)
        self.collectD_thread.daemon = True
        self.collectD_thread.start()


    def stopMeasurement(self):
        self.measuring = False
        try:
            self.collectD_thread.join()
        except Exception as e:
            printE(f'Error when joining thread:\n{e}')
        print('Thread joined')
        self.axes.closeOutputFile()

    def periodicCall(self):
        """
        Check every 200 ms if there is something new in the queue.
        """
        if self.running:
            self.interface.update()
            self.root.after(500, self.periodicCall)
        else:
            # DO SOME CLEANUP BEFORE CLOSING (and do it a bit nicer)
            if self.measuring:
                self.stopMeasurement()
            self.root.quit()
            self.root.destroy()
            print('!')
            sys.exit(1)

    def collectData(self):
        """
        Where we actually think about measuring things
        Measurements are made in both polarities
        Where the polarity is not specified, the measurement is made in the 
        first (positive/'Pos_') polarity, as this is the midpoint of the measurement for this data point
        (set current -wait> m1, set current -wait> m2)
        """
        self.axes.start_measurement = True
        while self.running and self.measuring:
            try:
                time.sleep(min(1, next_meas_time-time.time()))
                t = time.time()
                if t < next_meas_time:
                    continue

                # acquire from devices
                self.axes.lock.acquire()
                ax = self.axes.axes
                for dev in self.devices.values():
                    for a, d in zip(dev.titles, dev.read()):
                        if a not in ax:
                            ax[c_dir+a].data.append(d)
                        elif c_dir == 'Pos_':
                                ax[a].data.append(d)
                if c_dir == 'Pos_':
                    self.axes.axes.Time.data.append(t)
                    r = (ax.Pos_Voltage.data[-1]/ax.Pos_Current.data[-1])/2
                    ax.Resistance.data.append(r)
                else:  # if c_dir == 'Neg_':
                    r = (ax.Neg_Voltage.data[-1]/ax.Neg_Current.data[-1] + 
                         ax.Pos_Voltage.data[-1]/ax.Pos_Current.data[-1])/2
                    ax.Resistance.data[-1] = r
                    self.axes.writeOutputLine()
                    # TODO: RESISTIVITY!
                    # TODO: set r_meas in input file
                    # ax.Resistivity.data.append(?)
                    # factor = hlp.calcStructureFactor(R_meas/R_notmeas)
                    # dat['rho'] = dat['R']/R_meas  # to normalise things correctly
                    # dat['rho'] *= np.pi*thickness*1e-9/np.log(2) * (R_meas+R_notmeas)/2 * factor
                self.axes.updated = True
                self.lock.release()
                
                # open the next file etc.
            except NameError as e: # the try except should be faster than an if here
                if self.axes.lock.locked():
                    self.axes.lock.release()
                # traceback.print_exc()
                # we haven't defined some of the variables yet
                line_finish_time = next_meas_time = time.time()
                c_dir = 'Neg_'
                self.axes.start_measurement = True
                t = time.time()
            
            # the lock is acquired for all of this block
            self.axes.lock.acquire()
            c_dir = 'Neg_' if c_dir == 'Pos_' else 'Pos_'
            ax = self.axes
            inp = ax.input
            input_line = inp.dat[inp.index]
            ndtemp = input_line['T_end']
            mNum = inp.magicNumber

            if (ax.start_measurement or t >= line_finish_time or (
                    ndtemp and abs(ndtemp - ax.axes[mNum[
                        'T_sensor']].data[-1]) < mNum['T_threshold'])):
                if not ax.start_measurement:
                    inp.index += 1
                ax.start_measurement = False
                self.axes.openOutputFile()
                input_line = inp.dat[inp.index]
                if any([a!=a for a in input_line.values()]):
                    # we have run out of valid lines in the file
                    self.measuring = False
                    ax.lock.release()
                    break
                ax.lock.release()
                # and now we unlock it; nothing after this should effect things

                # there is a lot of stuff that needs to happen here
                if input_line['time_max']:
                    line_finish_time = t + input_line['time_max']
                else:
                    line_finish_time = t + mNum['time_giveup']
                if input_line['T_end']:
                    self.devices.temperature.set('ramp', input_line['T_ramp_rate'])
                    self.devices.temperature.set('setp', input_line['T_end'])

                self.devices.supply.set('voltage', input_line['V_limit'])
                self.devices.supply.set('switch', 1)
            
            # we just need to continue measureing for a bit longer
            if c_dir == 'Pos_':
                c_s = input_line['I_start']
                c_e = input_line['I_end']
                td = input_line['time_max']
                te = line_finish_time
                # calcuate the next current to apply
                current = c_e if t > te or td == 0 else (t-te+td)/td*(c_e-c_s) + c_s
            else:  # if c_dir == 'Neg_':
                # the opposite of what it was last time
                current = -ax.axes.Supply_Current.data[-1]
            self.devices.supply.set('current', current)
            next_meas_time += input_line['time_datapoint']

        # tidy up on exit
        self.devices.supply.set('switch', 0)

    def stopApplication(self):
        self.running = False


    
    def initialiseDevices(self):
        """ Initialise the devices used to read data """
        self.rm = pyvisa.ResourceManager()  # might need path to lib or '@py'
        self.devices = DotDict({})
        self.devices.supply = SimpleDevice(
                self.rm, 'GPIB::16::INSTR', # it says 9 on the box?
                config=['G0X'], 
                read=('',),
                # cast=lambda x: (x[0], float(x[4:14]), float(x[16:26]), float(x[28:38])),
                cast=lambda x: (y:=x[0].split(','), 1 if y[0][0]=='O' else 0, float(y[0][4:]),
                                float(y[1][1:]), float(y[2][1:]))[1:],
                titles=('Overcompliance', 'Supply_Current', 'Supply_Voltage',
                        'Supply_Time'),
                setthing={'current': 'I{:+.3E}X', 'voltage': 'V{:+.4E}X', # voltage must be integer?
                          'switch': 'F{:1d}X'}
                )
        self.devices.amps = SimpleDevice(
                self.rm, 'GPIB::14::INSTR',
                config=['*rst; status:preset; *cls', 'CONFIGURE:CURRENT:DC'],
                read=('READ?',), cast=(lambda x: (float(x[0]),)), titles=('Current',),
                )
        self.devices.volts = SimpleDevice(
                self.rm, 'GPIB::7::INSTR',
                config=[],  # ['G1 B1 N1 O1 P2 S2 X'],
                # prefix on result, 6 1/2 digit display, Filters ON,
                # Analogue Filter ON, Digital filter high response, 100ms integration,
                # execute commands
                read=('',),
                cast=lambda x: (
                    x[0][0], a if abs(a:=float(x[0][4:]))<1e90 else a*float('inf')),
                titles=('Voltage_Prefix', 'Voltage'),
                setthing={'screen': "A1,'{}'X", 'screen_reset': 'AOX'}
                )
        self.devices.temperature = SimpleDevice(
                self.rm, 'GPIB::12::INSTR',
                config=('*RST', 'CSET 1, B, 1, 1', 'CDISP 1, 1, 25, 1', # change to actual resistance
                        'CLIMIT 1, 301.0, 11, 0, 4, 5', 'RANGE 5'),  # '*RST'
                read=('KRDG? A' ,'KRDG? B'),
                cast=lambda x: (float(x[0]), float(x[1])),
                titles=('Temperature_A', 'Temperature_B'),
                setthing={'ramp': 'RAMP 1, 1, {:.1f}',
                          'setp': 'SETP 1, {:.1f}', 'reset': '*RST'}
                )




if __name__ == '__main__':
    root = tk.Tk()
    meter = Meter(root)
    root.mainloop()

