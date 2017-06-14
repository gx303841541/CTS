#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""CTS schedule process
   by Kobe Gong. 2017-4-28
"""

import re
import os, time, datetime
import sys
import argparse
import signal
import common_tool.cprint as cprint
import common_tool.common_tool as common_tool
import report_tool.report as report
from log_tool.log_tool import my_logging
from task_tool.task import task
from cli_tool.cli_tool import my_cmd
from case_tool.case_tool import _nodes_resource, _cases_resource, case_handle
import my_socket.my_socket as my_socket
import threading, logging
import queue, yaml


class arg_handle():
    def __init__(self, name):
        self.p = cprint.cprint(name)
        self.parser = self.build_option_parser("-" * 50)

    def build_option_parser(self, description):
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument(
            '-p', '--server-port',
            dest='server_port',
            action='store',
            default=8888,
            type=int,
            help='Specify TCP server port',
        )

        parser.add_argument(
            '-i', '--server-IP',
            dest='server_IP',
            action='store',
            default='',
            help='Specify TCP server IP address',
        )

        parser.add_argument(
            '-r', '--role',
            dest='role',
            action='store',
            choices={'server', 'client', 'both'},
            required=True,
            help='Specify TCP server IP address',
        )

        parser.add_argument(
            '-w', '--way',
            dest='way',
            action='store',
            choices={'fixed', 'distribute', 'onebyone'},
            default='distribute',
            help='Specify how to schedule cases, "fixed", "distribute" are support now',
        )

        parser.add_argument(
            '-n', '--node_file',
            dest='node_file',
            action='store',
            default='node.yaml',
            help='Specify node info',
        )

        parser.add_argument(
            '-c', '--case_file',
            dest='case_file_list',
            action='append',
            metavar='pattern', 
            #required=True,
            default=['case.yaml'],
            help='Specify all case info',
        )
        
        parser.add_argument(
            '-m', '--mix_case_file',
            dest='mix_case_file',
            action='store',
            help='Get case ids from a file, then store to case.yaml',
        ) 
        return parser

    def get_args(self, attrname):
        return getattr(self.args, attrname)

    def check_args(self):

        #To kill old instance
        self_pid = os.getpid()
        LOG.p.critical("Self PID %s..." % (self_pid))
        active_instance = common_tool.my_system("ps -ef |  grep -E CTS.py | grep -E -v 'grep|dtach'")
        for old_pid in re.finditer(r'^root\s+(\d+)', active_instance, re.M):
            if old_pid.group(1) == str(self_pid):
                continue
            else:
                LOG.p.critical("To kill %s..." % (old_pid.group(1)))
                common_tool.my_system("kill -9 %s" % (old_pid.group(1)))



        if arg_handle.get_args('role') in ['server', 'both']:
            if os.path.exists(self.get_args('node_file')):
                pass
            else:
                self.p.error_p("node file not exist!")
                sys.exit(1)

            if self.get_args('mix_case_file'):
                mix_case_file = self.get_args('mix_case_file')
                LOG.p.info("Use %s to create case.yaml" % (mix_case_file))

                all_cts_case_file = re.findall(r'(TestSuite_\w+_\w+\.cts)', common_tool.my_system("ls /opt/cts/CTS/ssr_epdg/cts_cases"), re.S)
                for suite_file in all_cts_case_file:
                    LOG.p.info("Found suite file: %s" % (suite_file))

                yaml_file = {}
                case_types = {
                    'L': 'large',
                    'S': 'small',
                    'ICR': 'icr',
                    'T': 'twag',
                }
                with open(mix_case_file, 'r') as m:
                    for line in m:
                        ids = re.findall(r'(\d{8})', line, re.M)
                        for id in ids:
                            #LOG.p.info("Found case: %s" % (id))
                            for suite_file in all_cts_case_file:
                                with open("/opt/cts/CTS/ssr_epdg/cts_cases/%s" % (suite_file), 'r') as s:
                                    if id in [i.strip() for i in s.readlines()]:
                                        case_type = re.findall(r'_([A-Z]+)\.cts', suite_file, re.M)[0]
                                        case_type = case_types[case_type]        
                                        yaml_file[id] = case_type
                                        LOG.p.info("Found case: %s in %s" % (id, suite_file))
                                    else:
                                        continue
                with open('case.yaml', 'w') as c:
                    yaml.dump(yaml_file, c) 

            for case_file in self.get_args('case_file_list'):
                if os.path.exists(case_file):
                    pass
                else:
                    self.p.error_p("case file: " + case_file + " not exist!")
                    sys.exit(1)
           

    def run(self):
        self.args = self.parser.parse_args()
        self.p.warning_p("CMD line: " + str(self.args))
        self.check_args()


class data_centre():
    def __init__(self, node_file, *case_file_list):
        self.node_resource = _nodes_resource(node_file)
        self.node_resource()
        self.case_resource = _cases_resource(*case_file_list)
        self.case_resource()


class schedule_centre():
    def __init__(self, data_centre, types, semaphore, way):
        self.data_centre = data_centre
        self.types = types
        self.semaphore = semaphore
        self.way = way

    def run_forever(self):
        self.semaphore.acquire()
        tmp_list = []
        caseid = 1

        if self.way == "onebyone":
            has_case = 'yes'
            while has_case:
                case = self.data_centre.case_resource.get_next_case(self.types)
                has_case = case
                if case:
                    LOG.p.debug("To run case:" + case)     
                    is_done = 'no'                
                    while is_done == 'no':
                        found_node = 'no'
                        for node in self.data_centre.node_resource.get_all_nodes():
                            if self.data_centre.node_resource.get_node_state(node) in ['active'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                                LOG.p.info("Run health check case: " + health_check_case + ' on ' + self.data_centre.node_resource.get_hostname(node)) 
                                self.data_centre.node_resource.add_data_out(node, health_check_case + ' ')
                                self.data_centre.node_resource.set_node_state(node, 'testing')
                            elif (self.data_centre.node_resource.get_hostname(node) in self.data_centre.case_resource.get_run_node(case) 
                                or node in self.data_centre.case_resource.get_run_node(case)) and self.data_centre.node_resource.get_node_state(node) in ['idle'] and len(self.data_centre.node_resource.get_all_narmal_nodes(self.types)) > self.data_centre.case_resource.get_run_times(case):
                                found_node = 'yes'
                                LOG.p.debug("%s has failed on node: %s, so skip this node now." % (case, node))
                                continue
                            elif self.data_centre.node_resource.get_node_state(node) in ['idle'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                                self.data_centre.case_resource.set_case_state(case, 'running')
                                self.data_centre.case_resource.set_run_times(case)
                                self.data_centre.case_resource.set_run_node(case, node)
                                #self.data_centre.case_resource.set_run_node(case, self.data_centre.node_resource.get_hostname(node)) 
                                self.data_centre.node_resource.add_data_out(node, case + ' ')
                                self.data_centre.node_resource.set_node_state(node, 'working')
                                self.data_centre.node_resource.add_ran_case(node, case)
                                LOG.p.info("Run case: " + case + ' on ' + self.data_centre.node_resource.get_hostname(node))     
                                is_done = 'yes'
                                found_node = 'yes'
                                break
                            elif self.data_centre.node_resource.get_node_type(node) == self.types:
                                LOG.p.debug(node + " in state:" + self.data_centre.node_resource.get_node_state(node))
                        
                        if found_node == 'yes':
                            break
                        elif is_done == 'no':
                            #LOG.p.error("No available %s node for case: %s! please to check these kinds of node!" % (self.types, case))
                            time.sleep(5)

                if has_case:
                    continue

                for case in self.data_centre.case_resource.get_case_by_state('running'):
                    if (self.data_centre.node_resource.get_node_state((self.data_centre.case_resource.get_run_node(case))[-1]) != 'working'
                        and self.data_centre.case_resource.get_case_state(case) == 'running' and self.data_centre.case_resource.get_case_type(case) == self.types):
                        LOG.p.error("%s maybe has lost result, set it to ongoing!" % (case))
                        self.data_centre.case_resource.set_case_state(case, 'ongoing')
                        has_case = 'yes'
                        continue
                    LOG.p.debug("%s is still runing, wait it finish!" % (case))
                    has_case = 'yes'
                    time.sleep(1)

        elif self.way == "fixed":
            has_case = 'yes'
            while has_case:
                case = self.data_centre.case_resource.get_one_case(self.types)
                has_case = case
                if case:
                    LOG.p.debug("To run case:" + case)     
                    is_done = 'no'                
                    while is_done == 'no':
                        found_node = 'no'
                        for node in self.data_centre.node_resource.get_all_nodes():
                            if self.data_centre.node_resource.get_node_state(node) in ['active'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                                LOG.p.info("Run health check case: " + health_check_case + ' on ' + self.data_centre.node_resource.get_hostname(node)) 
                                self.data_centre.node_resource.add_data_out(node, health_check_case + ' ')
                                self.data_centre.node_resource.set_node_state(node, 'testing')

                            elif self.data_centre.node_resource.get_node_state(node) in ['idle'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                                self.data_centre.node_resource.set_node_state(node, 'working')
                                self.data_centre.case_resource.set_case_state(case, 'running')
                                self.data_centre.case_resource.set_run_times(case)
                                self.data_centre.case_resource.set_run_node(case, node)
                                #self.data_centre.case_resource.set_run_node(case, self.data_centre.node_resource.get_hostname(node)) 
                                self.data_centre.node_resource.add_data_out(node, case + ' ')
                                self.data_centre.node_resource.add_ran_case(node, case)
                                LOG.p.info("Run case: " + case + ' on ' + self.data_centre.node_resource.get_hostname(node))     
                                is_done = 'yes'
                                found_node = 'yes'
                                break
                            elif self.data_centre.node_resource.get_node_type(node) == self.types:
                                LOG.p.debug(node + " in state:" + self.data_centre.node_resource.get_node_state(node))
                        
                        if found_node == 'yes':
                            break
                        elif is_done == 'no':
                            #LOG.p.error("No available %s node for case: %s! please to check these kinds of node!" % (self.types, case))
                            time.sleep(5)

                if has_case:
                    continue

                for case in self.data_centre.case_resource.get_case_by_state('running'):
                    if (self.data_centre.node_resource.get_node_state((self.data_centre.case_resource.get_run_node(case))[-1]) != 'working'
                        and self.data_centre.case_resource.get_case_state(case) == 'running' and self.data_centre.case_resource.get_case_type(case) == self.types):
                        LOG.p.error("%s maybe has lost result, set it to ongoing!" % (case))
                        self.data_centre.case_resource.set_case_state(case, 'ongoing')
                        has_case = 'yes'
                        continue
                    LOG.p.debug("%s is still runing, wait it finish!" % (case))
                    has_case = 'yes'
                    time.sleep(1)

        else:
            for case in self.data_centre.case_resource.get_next_nostart_case(self.types):
                LOG.p.info("To run case:" + case)     
                is_done = 'no' 
                while is_done == 'no':       
                    for node in self.data_centre.node_resource.get_all_nodes():
                        if self.data_centre.node_resource.get_node_state(node) in ['active'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                            LOG.p.info("Run health check case: " + health_check_case + ' on ' + self.data_centre.node_resource.get_hostname(node)) 
                            self.data_centre.node_resource.add_data_out(node, health_check_case + ' ')
                            self.data_centre.node_resource.set_node_state(node, 'testing')
                        elif self.data_centre.node_resource.get_node_state(node) in ['idle'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                            self.data_centre.node_resource.set_node_state(node, 'working')
                            self.data_centre.case_resource.set_case_state(case, 'running')
                            self.data_centre.case_resource.set_run_times(case)
                            self.data_centre.case_resource.set_run_node(case, node)
                            #self.data_centre.case_resource.set_run_node(case, self.data_centre.node_resource.get_hostname(node))                       
                            self.data_centre.node_resource.add_data_out(node, case + ' ')
                            self.data_centre.node_resource.add_ran_case(node, case)
                            LOG.p.info("Run case: " + case + ' on ' + self.data_centre.node_resource.get_hostname(node)) 
                            is_done = 'yes'
                            break
                        elif self.data_centre.node_resource.get_node_type(node) == self.types:
                            LOG.p.debug(node + " in state:" + self.data_centre.node_resource.get_node_state(node))
                    if is_done == 'no':
                        time.sleep(5)

            LOG.p.info("All %s cases had finish the first round! Now, to re-run the failed cases if have!" % (self.types))

            has_case = 'yes'
            while has_case == 'yes':
                has_case = 'no'
                for case in self.data_centre.case_resource.get_next_fail_case(self.types):
                    has_case = 'yes'     
                    LOG.p.debug("To run case:" + case)     
                    is_done = 'no'                
                    while is_done == 'no':
                        found_node = 'no'
                        for node in self.data_centre.node_resource.get_all_nodes():
                            if self.data_centre.node_resource.get_node_state(node) in ['active'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                                LOG.p.info("Run health check case: " + health_check_case + ' on ' + self.data_centre.node_resource.get_hostname(node)) 
                                self.data_centre.node_resource.add_data_out(node, health_check_case + ' ')
                                self.data_centre.node_resource.set_node_state(node, 'testing')
                            elif (self.data_centre.node_resource.get_hostname(node) in self.data_centre.case_resource.get_run_node(case) 
                                or node in self.data_centre.case_resource.get_run_node(case)) and self.data_centre.node_resource.get_node_state(node) in ['idle'] and len(self.data_centre.node_resource.get_all_narmal_nodes(self.types)) > self.data_centre.case_resource.get_run_times(case):
                                found_node = 'yes'
                                LOG.p.debug("%s has failed on node: %s, so skip this node now." % (case, node))
                                continue
                            elif self.data_centre.node_resource.get_node_state(node) in ['idle'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                                self.data_centre.node_resource.set_node_state(node, 'working')
                                self.data_centre.case_resource.set_case_state(case, 'running')
                                self.data_centre.case_resource.set_run_times(case)
                                self.data_centre.case_resource.set_run_node(case, node)
                                #self.data_centre.case_resource.set_run_node(case, self.data_centre.node_resource.get_hostname(node)) 
                                self.data_centre.node_resource.add_data_out(node, case + ' ')
                                self.data_centre.node_resource.add_ran_case(node, case)
                                LOG.p.info("Run case: " + case + ' on ' + self.data_centre.node_resource.get_hostname(node))     
                                is_done = 'yes'
                                found_node = 'yes'
                                break
                            elif self.data_centre.node_resource.get_node_type(node) == self.types:
                                LOG.p.debug(node + " in state:" + self.data_centre.node_resource.get_node_state(node))
                        if found_node == 'yes':
                            break
                        elif is_done == 'no':
                            time.sleep(5)

                for case in self.data_centre.case_resource.get_case_by_state('running'):
                    if (self.data_centre.node_resource.get_node_state((self.data_centre.case_resource.get_run_node(case))[-1]) != 'working'
                        and self.data_centre.case_resource.get_case_state(case) == 'running' and self.data_centre.case_resource.get_case_type(case) == self.types):
                        LOG.p.error("%s maybe has lost result, set it to ongoing!" % (case))
                        self.data_centre.case_resource.set_case_state(case, 'ongoing')
                        has_case = 'yes'
                        continue
                    LOG.p.debug("%s is still runing, wait it finish!" % (case))
                    has_case = 'yes'
                    time.sleep(1)




        #It time to let slient exit!
        for node in self.data_centre.node_resource.get_all_nodes():
            if self.data_centre.node_resource.get_node_state(node) in ['active', 'testing', 'working', 'idle'] and self.data_centre.node_resource.get_node_type(node) == self.types:
                LOG.p.warning("It time to let %s exit!" % self.data_centre.node_resource.get_hostname(node)) 
                self.data_centre.node_resource.add_data_out(node, 'eeeeeeee ')

        self.semaphore.release()


class stastics_centre():
    def __init__(self, data_centre):
        self.data_centre = data_centre
        
    def run_forever(self):
        done_flag = 'no'
        while done_flag == 'no':     
            for node in self.data_centre.node_resource.get_all_nodes():
                if self.data_centre.node_resource.data_in_is_empty(node):
                    pass
                else:
                    result = self.data_centre.node_resource.get_data_in(node)
                    results = re.findall(r'(\d{8})\-([\w-]+)', result)
                    if results:
                        while results:
                            id, result = results[0]
                            results = results[1:]
                            node_state = 'idle'
                            if self.data_centre.case_resource.is_valid_case(id):
                                self.data_centre.case_resource.set_case_result(id, result)
                                if self.data_centre.case_resource.get_run_times(id) == self.data_centre.case_resource.get_max_try_times(id):
                                    self.data_centre.case_resource.set_case_state(id, 'done')
                                #self.data_centre.node_resource.add_ran_case(node, id)
                                self.data_centre.node_resource.set_node_statistics(node, result)
                                #self.data_centre.node_resource.set_node_state(node, 'idle')
                                LOG.p.info("Set case: " + id + ' ' + result)

                            #use for health check
                            if id in ['10000000', '20000000', health_check_case]:
                                if result != 'pass':
                                    node_state = 'active'
                                    LOG.p.critical("Node: %s health check fail!" % self.data_centre.node_resource.get_hostname(node))
                                else:
                                    LOG.p.info("Node: %s health check pass!" % self.data_centre.node_resource.get_hostname(node))

                            self.data_centre.node_resource.set_node_state(node, node_state)
                    else:
                        self.data_centre.node_resource.set_node_state(node, 'dead')
                        LOG.p.error("Unknow result: " + result)
                                   

def sys_proc(action="default"):
    global thread_ids
    thread_ids = []
    for th in thread_list:
        thread_ids.append(threading.Thread(target=th[0], args=th[1:]))

    for th in thread_ids:
        th.setDaemon(True)        
        th.start()
        time.sleep(1)

    #for th in thread_ids:        
    #    th.join() 


def run_forever(function):
    try:
        while True:
            function()
    except KeyboardInterrupt:
        sys.exit(0)
    
    
if __name__ == '__main__':
    #sys log init
    LOG = my_logging(__name__ + ".log", clevel=logging.INFO)
    LOG.p.info("Let's go!!!") 
    
    #arg init
    arg_handle = arg_handle("arg")
    arg_handle.run()

    #confirm log dir
    log_dir = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    global health_check_case
    health_check_case = '10000000'

    global thread_list
    thread_list = []
    if arg_handle.get_args('role') in ['server', 'both']:
        #server:    
        data_centre_handle = data_centre(arg_handle.get_args('node_file'), *(arg_handle.get_args('case_file_list')))

        my_server = my_socket.my_server((arg_handle.get_args('server_IP'), arg_handle.get_args('server_port')), data_centre_handle)
        thread_list.append([my_server.run_forever])


        #
        kinds = data_centre_handle.case_resource.get_cases_types()
        semaphore = threading.Semaphore(len(kinds))
        for kind in kinds:
            schedule_centre_handle = schedule_centre(data_centre_handle, kind, semaphore, arg_handle.get_args('way'))
            thread_list.append([schedule_centre_handle.run_forever])

        stastics_handle = stastics_centre(data_centre_handle)
        thread_list.append([stastics_handle.run_forever])

        report_handle = report.report(data_centre_handle, semaphore, try_times=len(kinds))
        thread_list.append([report_handle.run_onetimes])

        task_handle = task()
        thread_list.append([task_handle.task_proc])        
        
        sys_proc()

        #cmd loop    
        signal.signal(signal.SIGINT, lambda signal, frame: print("%s[32;2m%s%s[0m" % (chr(27), '\nExit CLI: CTRL+Q, Exit SYSTEM: quit!!!!', chr(27))))
        my_cmd = my_cmd(data_centre_handle, task_handle, report_handle)
        my_cmd.cmdloop()
        
    else:
        #client:
        case_in = queue.Queue()
        case_out = queue.Queue()
        my_client = my_socket.my_client((arg_handle.get_args('server_IP'), arg_handle.get_args('server_port')), case_in, case_out)
        thread_list.append([run_forever, my_client.run_forever])

        case_handle = case_handle(case_in, case_out, log_dir)
        thread_list.append([case_handle.run_forever])     
             
        task_handle = task()
        thread_list.append([task_handle.task_proc]) 
        
        sys_proc()
        
        for th in thread_ids:        
            th.join()        

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    
