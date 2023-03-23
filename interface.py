from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import figure
from tkinter import ttk
import tkinter as tk
import pandas as pd
import traceback
import code  # for debugging
# import numpy as np

from utility import DotDict, printE, tofloat
from axes import AxisFileGroup

class Interface:
    def __init__(self, root, quitFunction, startMeasurement, stopMeasurement, axes: AxisFileGroup):
        self.quitFunction = quitFunction
        self.startMeasurement = startMeasurement
        self.stopMeasurement = stopMeasurement
        self.axes = axes
        self.root = root
        self.root.title('Cryostat Resistivity measurement')
        
        # ===================================================================
        # create tabs
        self.tc = ttk.Notebook(root)
        self.t_controls = ttk.Frame(self.tc)
        self.t_plot = ttk.Frame(self.tc)
        self.tc.add(self.t_controls, text ='Controls')
        self.tc.add(self.t_plot, text ='Plot')
        self.tc.pack(expand = 1, fill ='both')

        # =====================================================================
        # settings for the controls tab
        self.fields = DotDict({})
        lb = tk.Label(self.t_controls, text='File Path Prefix:')
        lb.grid(column=0, row=0)
        en = tk.Entry(self.t_controls)
        en.insert(0, axes.file_path_prefix)
        en.grid(column=1, row=0)
        self.fields.file_path_prefix = en
        lb = tk.Label(self.t_controls, text='User:')
        lb.grid(column=0, row=1)
        en = tk.Entry(self.t_controls)
        en.insert(0, axes.file_user)
        en.grid(column=1, row=1)
        self.fields.file_user = en
        lb = tk.Label(self.t_controls, text='Sample:')
        lb.grid(column=0, row=2)
        en = tk.Entry(self.t_controls)
        en.insert(0, axes.file_sample)
        en.grid(column=1, row=2)
        self.fields.file_sample = en
        # lb = tk.Label(self.t_controls, text='Thickness [nm]:')
        # lb.grid(column=0, row=3)
        # en = tk.Entry(self.t_controls)
        # en.insert(0, axes.file_sample)
        # en.grid(column=1, row=3)
        # self.fields.sample_thickness = en
        # lb = tk.Label(self.t_controls, text='Other Resistance [Ω]:')
        # lb.grid(column=0, row=4)
        # en = tk.Entry(self.t_controls)
        # en.insert(0, axes.file_sample)
        # en.grid(column=1, row=4)
        # self.fields.sample_other_res = en

        self.measurement_is_started = False
        self.measurement_toggle_button = tk.Button(
                self.t_controls, text='Start Measurement', bg='red',
                command = self.measurement_toggle)
        self.measurement_toggle_button.grid(column=0, row=5, columnspan=2)
        

        # display the input file as a table
        self.t_c = DotDict({})
        self.t_c.tab_c = tk.Canvas(self.t_controls, bd=1, relief='sunken')
        self.t_c.tab_f = tk.Frame(self.t_c.tab_c)
        self.t_c.vsb = tk.Scrollbar(
                self.t_controls, orient='vertical', command=self.t_c.tab_c.yview)
        self.t_c.hsb = tk.Scrollbar(
                self.t_controls, orient='horizontal', command=self.t_c.tab_c.xview)
        self.t_c.tab_c.configure(yscrollcommand=self.t_c.vsb.set, xscrollcommand=self.t_c.hsb.set)
        
        self.t_c.tab_c.grid(row=0, column=3, columnspan=3, rowspan=7, sticky="nsew")
        self.t_c.vsb.grid(row=0, column=6, rowspan=7, sticky="ns")
        self.t_c.hsb.grid(row=7, column=3, columnspan=3, sticky="ew")
        self.t_controls.grid_rowconfigure(6, weight=1)
        self.t_controls.grid_columnconfigure(5, weight=1)
        self.t_c.tab_c.create_window((4,4), window=self.t_c.tab_f, anchor="nw")
        self.t_c.tab_f.bind("<Configure>", lambda event, c=self.t_c.tab_c:
                            c.configure(scrollregion=c.bbox("all")))
        self.t_c.index_var = tk.IntVar()


        self.fields.load_input = ttk.Button(
                self.t_controls, text='Load input file',
                command=self.loadInputFile)
        self.fields.load_input.grid(row=8, column=3)
        self.fields.save_input = ttk.Button(
                self.t_controls, text='Save input file',
                command=self.saveInputFile)
        self.fields.save_input.grid(row=8, column=4)
        self.fields.input_fname = tk.Label(self.t_controls, text='')
        self.fields.input_fname.grid(row=8, column=5)


        # TODO: possibly make time : temperature / current prediction?

        # =====================================================================
        # settings for the plot tab
        # we have to use pack here, since it's what matplotlib likes
        self.plot = DotDict({})
        self.plot.fig = figure.Figure(
                constrained_layout=True, figsize=(840/96, 480/96), dpi=96)
        self.plot.ax1 = self.plot.fig.add_subplot(1, 1, 1)
        self.plot.canvas = FigureCanvasTkAgg(self.plot.fig, self.t_plot)
        self.plot.canvas.draw()
        self.plot.canvas.get_tk_widget().pack(fill='both', expand=True)
        self.plot.toolbar = NavigationToolbar2Tk(self.plot.canvas, self.t_plot)
        self.plot.toolbar.update()
        # Add stuff to toolbar (dropdown to change the plot axis)
        self.yaxis_label = tk.Label(self.plot.toolbar, text='Y axis:')
        self.yaxis_label.pack(side=tk.LEFT)
        self.yaxis_is = tk.StringVar(self.plot.toolbar)
        self.yaxis_is.set('Pos_Voltage')  # 'Resistance'
        self.yaxis_options = tk.OptionMenu(
                self.plot.toolbar, self.yaxis_is, *self.axes.axes.keys(),
                command=lambda x, s=self: s.updatePlot(force=True))
        self.yaxis_options.pack(side=tk.LEFT)

        self.xaxis_label = tk.Label(self.plot.toolbar, text='X axis:')
        self.xaxis_label.pack(side=tk.LEFT)
        self.xaxis_is = tk.StringVar(self.plot.toolbar)
        self.xaxis_is.set('Temperature_B')
        self.xaxis_options = tk.OptionMenu(
                self.plot.toolbar, self.xaxis_is, *self.axes.axes.keys(),
                command=lambda x, s=self: s.updatePlot(force=True))
        self.xaxis_options.pack(side=tk.LEFT)
        self.axis_changed = False

        # =====================================================================
        # keybindings
        self.root.protocol("WM_DELETE_WINDOW", self.quitFunction)
        self.root.bind("<Control-w>", self.quitInterface)
        self.root.bind('<Control-Alt-Shift-T>', self.createTerminal)

        self.updatePlot(force=True)


    def changeInputLine(self):
        self.axes.lock.acquire()
        self.axes.input.index = self.t_c.index_var.get()
        self.axes.start_measurement = True
        self.axes.lock.release()


    def saveInputFile(self, file=None):
        file = file or tk.filedialog.asksaveasfilename()
        try:
            self.axes.input.writeInputFile(file)
        except Exception as e:
            tk.messagebox.showerror('Failed to write input file', 'Failed to write input file')
            printE(e)
            traceback.print_exc()
            return
        self.fields.input_fname.config(text=self.axes.input.fname)


    def loadInputFile(self, file=None):
        file = file or tk.filedialog.askopenfilename()
        try:
            self.axes.input.openInputFile(file)
        except Exception as e:
            tk.messagebox.showerror('Failed to read input file', 'Failed to read input file')
            printE(e)
            traceback.print_exc()
            return
        self.drawInputFile()
        self.fields.input_fname.config(text=self.axes.input.fname)


    def drawInputFile(self):
        [w.destroy() for w in self.t_c.tab_f.winfo_children()]
        f = self.t_c.tab_f
        self.t_c.table = (t:=[])  # a list of dicts
        for i_r, row in enumerate(self.axes.input.dat, start=1):
            t.append((ti:={}))
            tk.Radiobutton(
                    f, variable=self.t_c.index_var, value=i_r-1,
                    command=lambda s=self: s.changeInputLine()
                    ).grid(row=i_r, column=0)
            for i_c, (title, v) in enumerate(row.items(), start=1):
                if i_r == 1:
                    tk.Label(f, text=title).grid(row=0, column=i_c)
                b = tk.Entry(f)
                b.insert(0, v)
                b.grid(row=i_r, column=i_c)
                ti[title] = b
        # self.t_c.tab_c.update()


    def update_axis_fields(self):
        self.axes.file_path_prefix = self.fields.file_path_prefix.get()
        self.axes.file_user = self.fields.file_user.get()
        self.axes.file_sample = self.fields.file_sample.get()
        # self.axes.sample_thickness = self.fields.sample_thickness.get()
        # self.axes.sample_other_resistance = self.fields.sample_other_res.get()

        for t_r, a_r in zip(self.t_c.table, self.axes.input.dat):  # syncronise the two tables
            for k, v in t_r.items():
                a_r[k] = tofloat(v.get())


    def update(self):
        self.update_axis_fields()
        self.updatePlot()
        if self.axes.input.tryAddRowToTable():
            self.drawInputFile()
        self.axes.lock.acquire()
        self.t_c.index_var.set(self.axes.input.index)
        self.axes.lock.release()


    def measurement_toggle(self):
        if self.measurement_is_started:
            self.stopMeasurement()
            self.measurement_is_started = False
            self.measurement_toggle_button.configure(
                bg='red', text='Start Measurement')
        else:
            try:
                self.startMeasurement()
            except Exception as e:
                tk.messagebox.showerror('Failed to start measurement', e)
                printE(e)
                traceback.print_exc()
                return
            self.measurement_is_started = True
            self.measurement_toggle_button.configure(
                bg='green', text='Stop Measurement')


    def updatePlot(self, force=False):
        if not (self.axes.updated or force):
            return
        # self.axes.lock.acquire()
        self.axes.updated = False
        x = self.axes.axes[self.xaxis_is.get()]
        y = self.axes.axes[self.yaxis_is.get()]
        ax = self.plot.ax1
        ax.clear()
        ax.set_xlabel(x.ax_label)
        ax.set_xscale(x.ax_scale)
        ax.set_ylabel(y.ax_label)
        ax.set_yscale(y.ax_scale)
        l = min(len(x.data), len(y.data))
        ax.plot(x.data[:l], y.data[:l])
        # self.axes.lock.release()
        self.plot.canvas.draw()

    def createTerminal(self, event):
        printE('Hello! How terribly has your day been going?')
        code.interact(local=dict(globals(), **locals()))

    def quitInterface(self, event=None):
        print('Quitting...', end='')
        self.quitFunction()



if __name__ == '__main__':
    root = tk.Tk()
    Interface(root, None, exit)
    root.mainloop()

