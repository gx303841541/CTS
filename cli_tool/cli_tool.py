#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""cli tool
   by Kobe Gong. 2017-4-11
"""

import re
import os
import sys
import argparse
import common_tool.cprint as cprint
import common_tool.common_tool as common_tool
from log_tool.log_tool import my_logging
from cmd import Cmd
import subprocess


P = cprint.cprint()

class my_cmd(Cmd): 
    def __init__(self, data_centre, task_handle, report_handle):
        Cmd.__init__(self)
        self.prompt = "CTS>"
        self.data_centre = data_centre
        self.task_handle = task_handle
        self.report_handle = report_handle
          
    def help_listnode(self):  
        P.common_p("list the node state")     
      
    def do_listnode(self, arg, opts=None):  
        self.data_centre.node_resource.show_node_state(arg)

    def help_listcase(self):  
        P.common_p("list the case status")
      
    def do_listcase(self, arg, opts=None):  
        self.data_centre.case_resource.show_case_info(arg)

    def help_listnodes(self):  
        P.common_p("list all the nodes state")     
      
    def do_listnodes(self, arg, opts=None):  
        self.data_centre.node_resource.show_nodes_state()

    def help_listcases(self):  
        P.common_p("list all the cases status")
      
    def do_listcases(self, arg, opts=None):  
        self.data_centre.case_resource.show_cases_info()

    def help_listfailcases(self):  
        P.common_p("list all the fail cases status")
      
    def do_listfailcases(self, arg, opts=None):  
        self.data_centre.case_resource.show_case_info_by_result('fail')        

    def help_listpasscases(self):  
        P.common_p("list all the pass cases status")
      
    def do_listpasscases(self, arg, opts=None):  
        self.data_centre.case_resource.show_case_info_by_result('pass')
        
    def help_listongoingcases(self):  
        P.common_p("list all the ongoing cases status")
      
    def do_listongoingcases(self, arg, opts=None):  
        self.data_centre.case_resource.show_case_info_by_state('ongoing')
        self.data_centre.case_resource.show_case_info_by_state('running')

    def help_showreport(self):  
        P.common_p("show a report about all cases")
      
    def do_showreport(self, arg, opts=None):  
        self.data_centre.case_resource.show_report()
  
    def help_givereport(self):  
        P.common_p("give a report about all cases")
      
    def do_givereport(self, arg, opts=None):  
        self.report_handle.give_report()        

    def help_addtask(self):  
        P.common_p("add a task by: name, func, run_time, interval, *argv")
      
    def do_addtask(self, arg, opts=None):
        P.notice_p("add a task: " + arg) 
        self.task_handle.add_task(*(arg.split()))
        
    def help_deltask(self):  
        P.common_p("del a task by task name")
      
    def do_deltask(self, arg, opts=None):  
        self.task_handle.del_task(arg)        
 
    def help_listtask(self):  
        P.common_p("list all tasks")
      
    def do_listtask(self, arg, opts=None):  
        self.task_handle.show_tasks() 

    def help_stopnode(self):  
        P.common_p("Will send 'eeeeeeee' to the given node(s)")
      
    def do_stopnode(self, arg, opts=None):
        if arg == 'all':
            self.data_centre.node_resource.add_case_to_nodes('eeeeeeee')    
        else:   
            self.data_centre.node_resource.add_case_to_node(arg, 'eeeeeeee')

    def default(self, arg, opts=None):
        try:
            subprocess.call(arg, shell=True)
        except:
            pass       
 
    def emptyline(self):
        pass
      
    def help_exit(self):
        P.common_p("Will exit CTS")
      
    def do_exit(self, arg, opts=None): 
        P.notice_p("It is time to say goodbye!")
        sys.exit()  



if __name__ == '__main__':
    pass
    
    
