# -*- coding: utf-8 -*-

"""common tool
by Kobe Gong. 2017-4-28
"""

import queue
import threading
import psycopg2

import fcntl, re
from subprocess import *

def file_lock(open_file):
    return fcntl.flock(open_file, fcntl.LOCK_EX | fcntl.LOCK_NB)

def file_unlock(open_file):
    return fcntl.flock(open_file, fcntl.LOCK_UN)  


lock = threading.Lock()
#lock.acquire()
#lock.release()


condition = threading.Condition()
#condition.acquire()
#condition.notify()
#condition.wait()
#condition.release()


#2 should == node/case types 
semaphore = threading.Semaphore(2)
#semaphore.acquire():
#semaphore.release()


def get_output(*popenargs, **kwargs):
    process = Popen(*popenargs, stdout=PIPE, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    return output

#run a cmd and check exec result
def my_system(*cmd):
    return check_output(*cmd, universal_newlines=True, shell=True)
    

#run a cmd without check exec result
def my_system_no_check(*cmd):
    return get_output(*cmd, universal_newlines=True, shell=True)
    
    

class db_handle:
    def __init__(self, db_type='xx', host="127.0.0.1", user='postgres', password='', db="Wireless_3G", port=5432):
        cxn = psycopg2.connect(database=db, user=user, password=password, host=host, port=port)
        cur = cxn.cursor()
        self.cxn = cxn
        self.cur = cur
       
    def db_query(self, cmd):
        self.cur.execute(cmd);
        return [item for item in self.cur.fetchall()]
   
    def db_close(self):
        self.cur.close()
        self.cxn.close()
    
    
    
    
    
    
    
    
