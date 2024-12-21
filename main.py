import tkinter as tk
import tkinter.ttk as ttk
from tkinter import *
from tkinter import filedialog
from tkintertable import TableCanvas, TableModel
import reader
from reader import *

root = Tk()

load_data_from_yaml(get_file_path())
reader.create_gui(root)
root.mainloop()
