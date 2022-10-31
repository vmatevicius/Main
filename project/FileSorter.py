
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import shutil
from pathlib import Path
import string
import random

#Declaring variables that will serve as new paths for files we are going to sort
new_text_dir = "C:/Users/vytis/OneDrive/Desktop/Downloads/Text files"
new_video_dir = "C:/Users/vytis/OneDrive/Desktop/Downloads/Videos"
new_music_dir = "C:/Users/vytis/OneDrive/Desktop/Downloads/Music"
new_executables_dir = "C:/Users/vytis/OneDrive/Desktop/Downloads/Executables"
new_images_dir = "C:/Users/vytis/OneDrive/Desktop/Downloads/Images"
new_compressed_dir = "C:/Users/vytis/OneDrive/Desktop/Downloads/Compressed files"
#Declaring a variable that will serve as a path to the folder we are going to observe
downl_folder = "C://Users/vytis/Downloads"

#generates a random 2 symbol ID
def generate_id(size=2, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))
#changes the name of a file by adding generated random ID
def make_unique_name(filename):
    path = Path(filename)
    return path.with_stem(f"{path.stem}_{generate_id()}")

#defining a move function to move files
def move_file(dest, entry, name):
    #checks if a file already exists in the directory
    exists = os.path.exists(dest + "/" + name)
    if exists:
        #makes unique id and adds it to the name of the file if the file already exists
        new_name = make_unique_name(name)
        os.rename(entry, new_name)
    #moves files to their destinations
        return shutil.move(new_name, dest)
    return shutil.move(entry, dest)

class movehandler(FileSystemEventHandler):
    def on_modified(self, event):
        with os.scandir(downl_folder) as entries:
            #looping over all the files in downloads folder
            for entry in entries:
                name = entry.name
                #checks if the entry is a text file
                if name.endswith(('.txt', '.pdf', '.doc', '.docx')):
                    dest = new_text_dir
                    move_file(dest, entry, name)
                #checks if the entry is an audio file
                elif name.endswith(('.mp3', '.wav')):
                    dest = new_music_dir
                    move_file(dest, entry, name)
                #checks if the entry is an image
                elif name.endswith(('.jpg', '.png', '.jpeg', '.bmp', '.gif')):
                    dest = new_images_dir
                    move_file(dest, entry, name)
                #checks if the entry is a video file
                elif name.endswith(('.mp4', '.wmv', '.mov')):
                    dest = new_video_dir
                    move_file(dest, entry, name)
                #checks if the entry is an executable file
                elif name.endswith(('.exe', '.apk', '.bat', '.jar', '.bin', '.msi')):
                    dest = new_executables_dir
                    move_file(dest, entry, name)
                #checks if the entry is a compressed file
                elif name.endswith(('.zip', '.rar')):
                    dest = new_compressed_dir
                    move_file(dest, entry, name)


#creating event handler object
event_handler = movehandler()
#creating observer object
observer = Observer()
observer.schedule(event_handler, downl_folder, recursive=True)
observer.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()