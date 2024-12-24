import argparse
from tkinter import *
import reader

parser = argparse.ArgumentParser(description="Process command line arguments.")
parser.add_argument('file', type=str, nargs='?', default=None, help='the relative path to the save file (optional)')
parser.add_argument('-d', '--debug', action='store_true', help='debug mode')
parser.add_argument('-j', '--json-dump', action='store_true', help='save json data to file')
args = parser.parse_args()

print(args)
print(type(args))
print(f"File: {args.file}")
print(f"Debug Mode: {args.debug}")
print(f"JSON Dump: {args.json_dump}")

# Create the main tkinter window
root = Tk()
root.title("XCOM Soldier Viewer")

data = reader.load_data_from_yaml(reader.get_file_path(args), args, return_csv=True)
table = reader.TableWindow(root, data)
root.mainloop()
