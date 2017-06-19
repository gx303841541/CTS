#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""report tool
   by Kobe Gong. 2017-5-08
"""

import yaml, re, random, time
from log_tool.log_tool import my_logging
import common_tool.cprint as cprint
import threading
import socket
import queue
import common_tool.common_tool as common_tool
import logging
import copy
import decimal

LOG = my_logging(__name__ + '.log')
P = cprint.cprint("__name__")


class report():
    def __init__(self, data_centre, semaphore, try_times):
        self.data_centre = data_centre
        self.semaphore = semaphore
        self.try_times = try_times
        
    def run_onetimes(self):
        loop = 1
        time.sleep(1)
        for i in range(self.try_times):
            LOG.p.info("Report thread try unlock times: %d" % (i + 1))
            self.semaphore.acquire()
            LOG.p.info("Report thread has unlock times: %d" % (i + 1))
        while loop == 1:
            if self.data_centre.case_resource.is_all_cases_done():
                self.give_report()
                loop = 0
            else:
                LOG.p.info("It is time to give a report, but some cases still onging, wait...")
                time.sleep(30)
                continue
                
        for i in range(self.try_times):
            self.semaphore.release()
            return
        

    def give_report(self):
        LOG.p.info("It is time to give a report!")

        with open('case_result.yaml', 'w') as c:
            yaml.dump(self.data_centre.case_resource.cases, c)

        with open('node_result.yaml', 'w') as n:
            nodes_info = self.data_centre.node_resource.queues
            to_file = {}
            for node in nodes_info:
                to_file[node] = {}
                for item in nodes_info[node]:
                    if not item in ['conn', 'in', 'out']:
                        to_file[node][item] = nodes_info[node][item]
            yaml.dump(to_file, n)

        with open('report.log', 'w') as r:
            r.write('-' * 30 + '\n')
            states = {}
            states['not_start'] = 0
            states['running'] = 0
            rerults = {}
            rerults['pass'] = 0

            for id in self.data_centre.case_resource.get_all_cases():
                if self.data_centre.case_resource.get_case_state(id) in states:
                    states[self.data_centre.case_resource.get_case_state(id)] += 1
                else:
                    states[self.data_centre.case_resource.get_case_state(id)] = 1

                result = self.data_centre.case_resource.get_case_result(id)
                if result in rerults:
                    rerults[result] += 1
                else:
                    rerults[result] = 1
                        
            for item in sorted(states):
                r.write("    " + item.ljust(20) + ':' + str(states[item]).rjust(20) + '\n')
            r.write('-' * 30 + '\n')
                
            for item in sorted(rerults):
                r.write("    " + item.ljust(20) + ':' + str(rerults[item]).rjust(20) + '\n')
            r.write('-' * 30 + '\n')        
                
            r.write("    " + 'Total'.ljust(20) + ':' + str(len(list(self.data_centre.case_resource.get_all_cases()))).rjust(20) + '\n')
            with decimal.localcontext() as ctx:
                ctx.prec = 2
                if 'done' in states:
                    r.write("    " + 'Success Rate'.ljust(20) + ':' + ("%.2f" % (rerults['pass'] * 100.0 / (len(list(self.data_centre.case_resource.get_all_cases())) - states['not_start'] - states['running'])) + '%').rjust(20) + '\n')
                    r.write("    " + 'Progress Rate'.ljust(20) + ':' + ("%.2f" % (states['done'] * 100.0 / len(list(self.data_centre.case_resource.get_all_cases()))) + '%').rjust(20) + '\n')
                else:
                    r.write("    " + 'Success Rate'.ljust(20) + ':' + '0.00%'.rjust(20) + '\n')
                    r.write("    " + 'Progress Rate'.ljust(20) + ':' + '0.00%'.rjust(20) + '\n')      
            r.write('-' * 30 + '\n')

            r.write('=' * 60 + '\n')
            
            r_rerults = {}
            r_errors = {}
            total = 0
            nodes = {}
            for id in self.data_centre.case_resource.get_all_cases():
                result = self.data_centre.case_resource.get_case_result(id)
                if self.data_centre.case_resource.get_run_node(id):
                    on_node = self.data_centre.node_resource.get_hostname(self.data_centre.case_resource.get_run_node(id)[-1])
                else:
                    on_node = 'xxxx'

                if on_node in nodes:
                    pass
                else:
                    nodes[on_node] = {
                        'pass': {},
                        'fail': {},
                    }
                

                ffd_id = id[:4]
                if result != 'pass':
                    total += 1

                    to_show = ("last fail on: %s" % (on_node)).rjust(40)
                    if ffd_id in r_rerults:
                        r_rerults[ffd_id][id] = result.ljust(20) + to_show
                    else:
                        r_rerults[ffd_id] = {id:result.ljust(20) + to_show}

                    if result in r_errors:
                        if ffd_id in r_errors[result]:
                            r_errors[result][ffd_id] += 1
                        else: 
                            r_errors[result][ffd_id] = 1
                    else:
                        r_errors[result] = {ffd_id: 1}

                    nodes[on_node]['fail'][id] = result
                else:
                    nodes[on_node]['pass'][id] = result


            for ffd_id in r_rerults:
                r.write("FFD%s: %d\n" % (ffd_id, len(r_rerults[ffd_id])))
                for id in sorted(r_rerults[ffd_id]):
                    r.write("\t%s: %s\n" % (id, r_rerults[ffd_id][id]))
                r.write('-' * 30 + '\n')

            r.write('=' * 30 + '\n')  

            for r_error in r_errors:
                counter = 0
                r.write("%s:\n" % (r_error))
                for ffd_id in sorted(r_errors[r_error]):
                    r.write("\t%s: %d\n" % (ffd_id, r_errors[r_error][ffd_id]))
                    counter += r_errors[r_error][ffd_id]
                r.write("\tTotal: %d\n" % (counter))
                r.write('-' * 30 + '\n')
            r.write('Total: %d\n' % (total)) 
            r.write('=' * 60 + '\n')

            for node in sorted(nodes):
                if node in ['xxxx']:
                    continue
                
                r.write("Node: %s\n" % (node))
                r.write("    " + 'pass'.ljust(20) + ':' + ('%d' % (len(nodes[node]['pass']))).rjust(20) + '\n')
                r.write("    " + 'fail'.ljust(20) + ':' + ('%d' % (len(nodes[node]['fail']))).rjust(20) + '\n')
                for id in sorted(nodes[node]['fail']):
                    r.write("    " * 2 + ('%s' % (id)).ljust(20) + '=' + ('%s' % (nodes[node]['fail'][id])).rjust(20) + '\n')
                r.write('-' * 30 + '\n')

            r.write('=' * 60 + '\n')
            LOG.p.info("Given report done!")
