import os
import glob

# Absolute path to the main log directory
main_log_dir = r"D:\Py_code\Stock_Trading_Auto\log"
# Relative path to the log directory (from this script's location)
local_log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'log'))
# Relative path to the files directory (from this script's location)
files_dir = os.path.join(os.path.dirname(__file__), '..', 'files')

def clear_directory(directory):
    print(f"Checking directory: {directory}")
    if not os.path.exists(directory):
        print(f"Directory does not exist: {directory}")
        return
    files = glob.glob(os.path.join(directory, '*'))
    print(f"Found files: {files}")
    for f in files:
        try:
            if os.path.isfile(f):
                os.remove(f)
                print(f"Deleted: {f}")
            elif os.path.isdir(f):
                # Optionally, clear subdirectories recursively
                subfiles = glob.glob(os.path.join(f, '*'))
                print(f"Found subfiles in {f}: {subfiles}")
                for subf in subfiles:
                    if os.path.isfile(subf):
                        os.remove(subf)
                        print(f"Deleted: {subf}")
        except Exception as e:
            print(f"Error deleting {f}: {e}")

if __name__ == '__main__':
    print("Clearing main log directory...")
    clear_directory(main_log_dir)
    print("Clearing local log directory...")
    clear_directory(local_log_dir)
    print("Clearing files directory...")
    clear_directory(files_dir)
    print("Cleanup complete.")
