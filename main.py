from tkinter import *
import reader

# Create the main tkinter window
root = Tk()
root.title("XCOM Soldier Viewer")

data = reader.load_data_from_yaml(reader.get_file_path(), return_csv=True)
table = reader.TableWindow(root, data)
root.mainloop()
