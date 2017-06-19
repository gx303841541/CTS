#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""task tool
   by Kobe Gong. 2017-5-10
"""
import re, sys, os, time
import yaml, re, random
from log_tool.log_tool import my_logging
import common_tool.cprint as cprint
import threading, logging


LOG = my_logging(__name__ + '.log', clevel=logging.INFO, flevel=logging.INFO)
P = cprint.cprint("__name__")

class task():
    def __init__(self, data_centre=None):
        self.data_centre = data_centre
        self.tasks = {}
        self.lock = threading.RLock()

    def add_task(self, name, func, run_time=1, interval=5, *argv):
        if name and func and int(run_time) >= 1 and int(interval) >= 1:
            pass
        else:
            LOG.p.error("Invalid task: %s, run_time: %d, internal: %d" % (name, int(run_time), int(interval)))
        self.lock.acquire()
        LOG.p.info("add task: %s, run_time: %d, internal: %d" % (name, int(run_time), int(interval)))
        self.tasks[name] = {
            'func'      : func,
            'run_time'  : int(run_time),                                        
            'interval'  : int(interval),
            'now_conter': 0,
            'argv'      : argv,
            'state'     : 'active'
        }
        self.lock.release()

    def del_task(self, name):
        self.lock.acquire()
        LOG.p.info("delete task:%s" % (name))
        if name in self.tasks:
            del self.tasks[name]
        self.lock.release()

    def show_tasks(self):
        if not self.tasks:
            P.notice_p("No task...")
        for task in self.tasks:
            P.notice_p(task + ":")
            for item in sorted(self.tasks[task]):
                P.notice_p("    " + item.ljust(20) + ':' + str(self.tasks[task][item]).rjust(20))

    def task_proc(self):
        while True:
            '''
            for task in self.tasks:
                if self.tasks[task]['state'] == 'inactive':
                    self.lock.acquire()
                    LOG.p.info("delete task: %s" % (task))
                    del self.tasks[task]
                    self.lock.release()
            '''
            if len(self.tasks) == 0:
                LOG.p.debug("No task!\n")

            for task in self.tasks:
                if self.tasks[task]['state'] == 'inactive':
                    continue
                self.lock.acquire()
                self.tasks[task]['now_conter'] += 1
                if self.tasks[task]['now_conter'] >= self.tasks[task]['interval']:               
                    if callable(self.tasks[task]['func']):
                        LOG.p.info("It is time to run %s: " % (task) + self.tasks[task]['func'].__name__ + str(self.tasks[task]['argv']))
                        self.tasks[task]['func'](*(self.tasks[task]['argv']))
                    else:
                        LOG.p.info("It is time to run %s: " % (task) + self.tasks[task]['func'] + str(self.tasks[task]['argv']))
                        eval(self.tasks[task]['func'] + '(*' + str(self.tasks[task]['argv']) + ')')
                    self.tasks[task]['now_conter'] = 0
                    self.tasks[task]['run_time'] -= 1
                    if self.tasks[task]['run_time'] == 0:
                        LOG.p.info("stop task:%s" % (task))
                        self.tasks[task]['state'] = 'inactive'
                self.lock.release()    
            time.sleep(1)


if __name__ == '__main__':
    task_sche = task_schedule();
    task_sche.add_task('task test', print, 3, 5, 'fuck me')
    task_sche.add_task('task test2', print, 4, 2, 'sleep me')
    task_sche.shcedule_task()
