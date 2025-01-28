import time
import logging
import multiprocessing
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

event_handler=LoggingEventHandler()
observer=Observer()

folder="C:/Users/M3N7OR/Desktop/Folder-monitoring"
folder1="C:/Users/M3N7OR/Desktop/Fldr-chks"


def monitor_folder(folder):
    logging.basicConfig(level=logging.INFO,filename="C:/Users/M3N7OR/Desktop/logs/mpfmr.log",filemode="w",
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    
    observer.schedule(event_handler, folder ,recursive=True)
    observer.start()

    try:
        print("Monitoring")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("Done")
    observer.join()

if __name__ == "__main__":
    m=multiprocessing.Process(target=monitor_folder,args=(folder,))
    print(" ")
    m1=multiprocessing.Process(target=monitor_folder,args=(folder1,))
    m.start()
    m1.start()