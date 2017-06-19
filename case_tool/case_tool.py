#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""case tool
   by Kobe Gong. 2017-5-01
"""

import yaml, re, random, sys, time, os
from log_tool.log_tool import my_logging
import common_tool.cprint as cprint
import common_tool.common_tool as common_tool
import threading
import socket
import queue
import functools
import logging
import decimal
import subprocess

my_lock = threading.Lock()
cases_lock = threading.Lock()
case_lock = threading.Lock()
#mylock.acquire()
#mylock.release()

LOG = my_logging(__name__ + '.log', clevel=logging.INFO)
P = cprint.cprint("__name__")

def need_add_lock(lock):
    def sync_with_lock(func):
        @functools.wraps(func)
        def new_func(*args, **kwargs):
            #LOG.p.critical(str(lock) + str(func))
            lock.acquire()
            try:
                return func(*args, **kwargs)
            finally:
                #LOG.p.error(str(lock) + str(func))
                lock.release()

        return new_func
    return sync_with_lock


CASE_STATE = ['not_start', 'ongoing', 'running', 'done']
class _case_state():
    def __init__(self, id, types, max_try_times=3, run_times=0,
                state='not_start'):
        self.id = id
        self.types = types
        self.max_try_times = max_try_times
        self.run_times = run_times

        #not_start, ongoing, done
        self.state = state

        self.run_node = []

        #None, pass, others
        self.results = []

    def get_case_state(self):
        return self.state

    @need_add_lock(case_lock)
    def set_case_state(self, new_state):
        if new_state in CASE_STATE:
            self.state = new_state
            return True
        else:
            LOG.p.warn(new_state + " is invalid state!")
            return False

    @need_add_lock(case_lock)
    def get_case_result(self):
        if 'pass' in self.results:
            return 'pass'
        elif len(self.results):
            return self.results[-1]
        else:
            return 'empty'

    @need_add_lock(case_lock)
    def set_case_result(self, result):
        self.results.append(result)

    def get_max_try_times(self):
        return self.max_try_times

    def get_run_times(self):
        return self.run_times

    def get_case_type(self):
        return self.types

    @need_add_lock(case_lock)
    def set_run_times(self, times=99):
        if times != 99 and times < self.run_times:
            LOG.p.warn(self.id + " run times should't reduce!")
        if times == 99:
            self.run_times += 1
        else:
            self.run_times = times

    def get_run_node(self):
        return self.run_node

    @need_add_lock(case_lock)
    def set_run_node(self, node):
        self.run_node.append(node)


class _cases_resource():
    def __init__(self, *case_file_list):
        self.cases = {}
        self.case_file_list = case_file_list

    def __call__(self):
        for case_file in self.case_file_list:
            with open(case_file) as f:
                cases = yaml.load(f)
                for case in cases:
                    case = str(case)
                    if not case in ['10000000', '20000000']:
                        self.cases[case] = _case_state(case, cases[case])

    def is_valid_case(self, id):
        return id in self.cases

    @need_add_lock(cases_lock)
    def get_case_state(self, id):
        if id in self.cases:
            return self.cases[id].get_case_state()
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    @need_add_lock(cases_lock)
    def set_case_state(self, id, new_state):
        if id in self.cases:
            return self.cases[id].set_case_state(new_state)
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    def show_case_info_by_result(self, result):
        for id in self.cases:
            if (self.cases[id].get_case_result() == result) or (result == 'fail' and self.cases[id].get_case_result() != 'pass' and self.cases[id].get_case_result() != 'empty'):
                P.notice_p(id + ":")
                for item in self.cases[id].__dict__:
                    P.notice_p("    " + item.ljust(20) + ':    ' + str(getattr(self.cases[id], item)).ljust(20))

    @need_add_lock(cases_lock)
    def get_case_result(self, id):
        if id in self.cases:
            return self.cases[id].get_case_result()
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    @need_add_lock(cases_lock)
    def set_case_result(self, id, result):
        if id in self.cases:
            if result == 'pass':
                self.cases[id].set_case_state('done')
            elif self.cases[id].get_run_times() < self.get_max_try_times(id):
                self.cases[id].set_case_state('ongoing')
            else:
                self.cases[id].set_case_state('done')
            return self.cases[id].set_case_result(result)
        else:
            LOG.p.warn("Invalid case: " + id + result)
            return None

    def get_max_try_times(self, id):
        if id in self.cases:
            return self.cases[id].get_max_try_times()
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    def get_case_type(self, id):
        if id in self.cases:
            return self.cases[id].get_case_type()
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    @need_add_lock(cases_lock)
    def get_run_times(self, id):
        if id in self.cases:
            return self.cases[id].get_run_times()
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    @need_add_lock(cases_lock)
    def set_run_times(self, id, times=99):
        if id in self.cases:
            return self.cases[id].set_run_times(times)
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    @need_add_lock(cases_lock)
    def get_run_node(self, id):
        if id in self.cases:
            return self.cases[id].get_run_node()
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    @need_add_lock(cases_lock)
    def set_run_node(self, id, node):
        if id in self.cases:
            return self.cases[id].set_run_node(node)
        else:
            LOG.p.warn("Invalid case: " + id)
            return None

    @need_add_lock(cases_lock)
    def get_case_by_state(self, state):
        ids = []
        for id in self.cases:
            if self.cases[id].get_case_state() != state:
                continue
            ids.append(id)
        return ids

    def show_case_info_by_state(self, state):
        for id in self.cases:
            if self.cases[id].get_case_state() != state:
                continue
            P.notice_p(id + ":")
            for item in self.cases[id].__dict__:
                P.notice_p("    " + item.ljust(20) + ':    ' + str(getattr(self.cases[id], item)).ljust(20))

    def show_case_info(self, id):
        if id in self.cases:
            P.notice_p(id + ":")
            for item in self.cases[id].__dict__:
                P.notice_p("    " + item.ljust(20) + ':    ' + str(getattr(self.cases[id], item)).ljust(20))

        else:
            P.common_p("Invalid case!")

    def show_cases_info(self):
        for id in self.cases:
            self.show_case_info(id)
            P.common_p('-' * 30)

    def is_all_cases_done(self):
        for id in self.cases:
            if self.get_case_state(id) != 'done':
                return False
        return True

    def get_case_info(self, id):
        if id in self.cases:
            return {item : getattr(self.cases[id], item) for item in self.cases[id].__dict__}
        else:
            LOG.p.error("Invalid case!")

    def get_all_cases(self):
        for id in self.cases:
            yield(id)

    def get_cases_types(self):
        number = {}
        for id in self.cases:
            number[self.cases[id].get_case_type()] = 1
        return number

    def get_one_case(self, case_type):
        for id in sorted(self.cases):
            if (self.get_case_state(id) == 'not_start' and self.get_case_type(id) == case_type) or (self.get_case_state(id) != 'running' and self.get_case_state(id) != 'done' and self.get_case_result(id) != 'pass' and self.get_run_times(id) < self.get_max_try_times(id) and self.get_case_type(id) == case_type):
                return(id) 
        return None

    def get_next_case(self, case_type):
        for id in sorted(self.cases):
            if (self.get_case_state(id) == 'not_start' and self.get_case_type(id) == case_type) or (self.get_case_state(id) != 'running' and self.get_case_state(id) != 'done' and self.get_case_result(id) != 'pass' and self.get_run_times(id) < self.get_max_try_times(id) and self.get_case_type(id) == case_type):
                yield(id)
        return None

    def get_next_nostart_case(self, case_type):
        for id in sorted(self.cases):
            if self.get_case_state(id) == 'not_start' and self.get_case_type(id) == case_type:
                yield(id)

    def get_next_fail_case(self, case_type):
        for id in sorted(self.cases):
            if self.get_case_state(id) != 'running' and self.get_case_state(id) != 'done' and self.get_case_result(id) != 'pass' and self.get_run_times(id) < self.get_max_try_times(id) and self.get_case_type(id) == case_type:
                yield(id)

    def show_report(self):
        P.common_p('-' * 30)
        states = {}
        states['not_start'] = 0
        states['running'] = 0
        rerults = {}
        rerults['pass'] = 0
        for id in self.cases:
            if self.get_case_state(id) in states:
                states[self.get_case_state(id)] += 1
            else:
                states[self.get_case_state(id)] = 1

            if self.get_case_result(id) in rerults:
                rerults[self.get_case_result(id)] += 1
            else:
                rerults[self.get_case_result(id)] = 1

        for item in sorted(states):
            P.notice_p("    " + item.ljust(20) + ':' + str(states[item]).rjust(20))
        P.common_p('-' * 30)

        for item in sorted(rerults):
            P.notice_p("    " + item.ljust(20) + ':' + str(rerults[item]).rjust(20))
        P.common_p('-' * 30)

        P.notice_p("    " + 'Total'.ljust(20) + ':' + str(len(self.cases)).rjust(20))
        with decimal.localcontext() as ctx:
            ctx.prec = 2
            if 'done' in states:
                P.common_p("    " + 'Success Rate'.ljust(20) + ':' + ("%.2f" % (rerults['pass'] * 100.0 / (len(self.cases)- states['not_start'] - states['running'])) + '%').rjust(20), fore='purple')
                P.common_p("    " + 'Progress Rate'.ljust(20) + ':' + ("%.2f" % (states['done'] * 100.0 / len(self.cases)) + '%').rjust(20), fore='cyan')
            else:
                P.common_p("    " + 'Success Rate'.ljust(20) + ':' + '0.00%'.rjust(20), fore='purple')
                P.common_p("    " + 'Progress Rate'.ljust(20) + ':' + '0.00%'.rjust(20), fore='cyan')
        P.common_p('-' * 30)


NODE_STATE = ['unreachable', 'active', 'testing', 'working', 'idle', 'dead']
class _nodes_resource():
    def __init__(self, node_file):
        self.node_file = node_file

    def __call__(self):
        with open(self.node_file) as f:
            nodes = yaml.load(f)
            queues = {}
            for node in nodes:
                if re.match(r'^[\d.]+|[a-fA-F:]+$', node):
                    ip = node
                    host = gethostbyaddr(ip)
                else:
                    host = node
                    ip = gethostbyname(node)

                queues[ip] = {
                    'in' : queue.Queue(),
                    'out' : queue.Queue(),

                    #'conn' : connection,
                    'state' : 'unreachable',
                    'hostname' : host,
                    'ip'    : ip,
                    'type'  : nodes[node],
                    'cases' : [],
                    'cases_statistics' : {
                        'pass'  : 0,
                        'total' : 0,
                    },
                    'health_check_sw': 'off',
                }
            self.queues = queues

    def is_available_node(self, ip):
        return ip in self.queues

    def get_all_nodes(self):
        return (node for node in self.queues)

    def get_all_narmal_nodes(self, node_type):
        narmal_nodes = []
        for node in self.queues:
            if self.get_node_type(node) == node_type and self.get_node_state(node) in ['working', 'idle']:
                narmal_nodes.append(node)
        return narmal_nodes

    @need_add_lock(my_lock)
    def get_node_state(self, node):
        if node in self.queues:
            return self.queues[node]['state']
        else:
            LOG.p.warn("Invalid node: " + node)
            return None

    def get_node_type(self, node):
        if node in self.queues:
            return self.queues[node]['type']
        else:
            LOG.p.warn("Invalid node: " + node)
            return None

    def get_node_state(self, node):
        if node in self.queues:
            return self.queues[node]['state']
        else:
            LOG.p.warn("Invalid node: " + node)
            return None

    @need_add_lock(my_lock)
    def set_node_state(self, node, new_state):
        if new_state in NODE_STATE:
            if node in self.queues:
                self.queues[node]['state'] = new_state
            else:
                LOG.p.warn("Invalid node: " + node)
        else:
            LOG.p.warn(new_state + " is invalid state!")

    def get_health_check_sw(self, node):
        if node in self.queues:
            return self.queues[node]['health_check_sw']
        else:
            LOG.p.warn("Invalid node: " + node)
            return None

    @need_add_lock(my_lock)
    def set_health_check_sw(self, node, value):
        if value in ['on', 'off']:
            if node in self.queues:
                self.queues[node]['health_check_sw'] = value
            else:
                LOG.p.warn("Invalid node: " + node)
        else:
            LOG.p.warn(value + " is invalid value!")

    @need_add_lock(my_lock)
    def set_all_nodes_health_check_sw(self, value):
        if value in ['on', 'off']:
            for node in self.queues:
                self.queues[node]['health_check_sw'] = value
        else:
            LOG.p.warn(value + " is invalid value!")

    @need_add_lock(my_lock)
    def show_node_state(self, node):
        if node in self.queues:
            for item in sorted(self.queues[node]):
                P.notice_p("    " + item.ljust(20) + ':    ' + str(self.queues[node][item]).ljust(40))
        else:
            P.common_p("Invalid node!")

    def show_nodes_state(self):
        P.notice_p("All nodes state:")
        for node in self.queues:
            P.notice_p(node + ":")
            self.show_node_state(node)
            P.common_p("-" * 40)

    def add_data_in(self, node, data):
        self.queues[node]['in'].put(data)

    def get_data_in(self, node):
        return self.queues[node]['in'].get()

    def data_in_is_empty(self, node):
        return self.queues[node]['in'].empty()

    def add_data_out(self, node, data):
        self.queues[node]['out'].put(data)

    def get_data_out(self, node):
        return self.queues[node]['out'].get()

    def data_out_is_empty(self, node):
        return self.queues[node]['out'].empty()

    def get_conn(self, node):
        return self.queues[node]['conn']

    def set_conn(self, node, conn):
        self.queues[node]['conn'] = conn

    def get_hostname(self, node):
        return self.queues[node]['hostname']

    def set_hostname(self, node, hostname):
        self.queues[node]['hostname'] = hostname

    def set_ip(self, node, ip):
        self.queues[node]['ip'] = ip

    def add_ran_case(self, node, id):
        self.queues[node]['cases'].append(id)

    @need_add_lock(my_lock)
    def set_node_statistics(self, node, result):
        if node in self.queues:
            if result == 'pass':
                self.queues[node]['cases_statistics']['pass'] += 1
            self.queues[node]['cases_statistics']['total'] += 1
        else:
            LOG.p.warn("Invalid node: " + node)

    def get_nodes_types(self):
        number = {}
        for node in self.queues:
            number[self.queues[node]['type']] = 1
        return number


def gethostbyaddr(ip):
    return ip
    #return socket.gethostbyaddr(ip)[0]

def gethostbyname(host):
    return socket.gethostbyname(host)


class case_handle():
    def __init__(self, in_queue, out_queue, log_dir):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.log_dir = log_dir
        self.db_handle = common_tool.db_handle()
        common_tool.my_system_no_check('mkdir /opt/cts_log/%s' % (self.log_dir))
        self.result = open('/opt/cts_log/%s/result.log' % (self.log_dir), 'a')

    def run_case(self, id):
        LOG.p.info("Run: %s" % id)
        try:
            common_tool.my_system_no_check("cd /opt/cts/installation_files && ./case_tool.pl -a %s && cd -" % (id))
            return common_tool.my_system_no_check("/opt/cts/cts_adaptor.pm -t %s -f /opt/cts_log/%s" % (id, self.log_dir))
        except Exception as e:
            LOG.p.warning("Run caseid: %s has error [%s]" % (id, e))

    def get_exec_id(self, id):
        last_case_info = common_tool.my_system("ls /opt/cts_log/%s -ltr | grep %s | sort" % (self.log_dir, id))
        if last_case_info:
            r = re.match('^.*cts-(?P<execid>\d+)-%s.*$' % (id.strip()), last_case_info, re.S | re.U)
            if r:
                LOG.p.info("Get execid: %s for caseid: %s" % (r.group('execid'), id))
                return r.group('execid')
            else:
                LOG.p.warning("Exec fail for caseid: %s [%s]" % (id, last_case_info))
                return None
        else:
            LOG.p.warning("Get execid failed for caseid: %s [%s]" % (id, last_case_info))
            return None

    def get_error_info(self, execid, caseid):
        return self.db_handle.db_query("SELECT error from errors where execution_id=%s and testcase_id=%s;" % (execid, caseid))

    def get_results_by_dir(self, dir):
        all_info = my_system("cd %s; ls" % (dir))
        #all_info = my_system("ls")

        result_info = {}
        result_show = {}

        for item in re.finditer(r'cts\-(\d+)\-(\d+)', all_info, re.S):
            exec_id, case_id = item.groups()
            #p.notice_p('%s %s' % (exec_id, case_id))
            result_info[(exec_id, case_id)] = self.get_error_by_id(exec_id, case_id)
            result_show[(exec_id, case_id)] = self.result_judge(exec_id, case_id, result_info[(exec_id, case_id)])

        if len(result_show):
            self.result_maker(result_show)
            P.notice_p("Create cts.result done!\n")
        else:
            P.warning_p("No result for %s" % dir)

    def select_result(self, exec_id, case_id, error_list):
        result = 'NONE'
        cts_results = self.db_handle.db_query("SELECT result from results where execution_id=%s and testcase_id=%s and level=2;" % (exec_id, case_id));
        for i in cts_results:
            v, *o = i
            if v == 1:
                result = 'pass'

        if len(error_list):
            for record in error_list:
                error_record = str(record[0])
                if re.search(r'Crashfile found', error_record, re.I | re.M):
                    result = 'crash-found'
                    break

                elif re.search(r'no memory name|memory check failed|ListPool check fail|DumpRegion check fail', error_record, re.I | re.S | re.U):
                    result = 'memory-leak'
                    break

                elif re.search(r'board \d+ state ERR!!!|Not active epdg process', error_record, re.I | re.M):
                    result = 'asp-state'
                    break

                elif re.search(r'ICR state', error_record, re.I | re.M):
                    result = 'ICR-state'
                    break

                elif re.search(r'keys not same|just exist in', error_record, re.I | re.M):
                    result = 'compare-fail'
                    break

                elif re.search(r'Missing parameter', error_record, re.I | re.M):
                    result = 'para-miss'
                    break

                elif re.search(r'bad user\/passwd', error_record, re.I | re.M):
                    result = 'SSH-fail'
                    break

                elif re.search(r'oam_CLI_send_cmd Send command|Check cli', error_record, re.I | re.M):
                    result = 'CLI-fail'
                    break

                elif re.search(r'call online failed', error_record, re.I | re.M):
                    result = 'online-fail'
                    break

                elif re.search(r'call offline failed', error_record, re.I | re.M):
                    result = 'offline-fail'
                    break

                elif re.search(r'Compare the template with|cmp_message_blk::', error_record, re.I | re.M):
                    result = 'compare-fail'
                    break

                elif re.search(r'PING6', error_record, re.I | re.M):
                    result = 'ping6-fail'
                    break

                elif re.search(r'ping', error_record, re.I | re.M):
                    result = 'ping-fail'
                    break

                elif re.search(r'expect[^\r\n]+TIMEOUT!', error_record, re.I | re.M):
                    result = 'timeout-happen'
                    break

                elif re.search(r'_http_', error_record, re.I | re.M):
                    result = 'http-fail'
                    break

                elif re.search(r'get ftp failed', error_record, re.I | re.M):
                    result = 'ftp-fail'
                    break

                elif re.search(r'get_protocol_message_by_types:: could not get the', error_record, re.I | re.M):
                    result = 'capture-miss'
                    break

                elif re.search(r'cert|pki cert|private.key|csr.pem', error_record, re.I | re.M):
                    result = 'cert-issue'
                    break

                elif re.search(r'Check IKE|IKE', error_record, re.I | re.M):
                    result = 'IKE-check'
                    break

                elif re.search(r'unreachable list|pgw unreachable', error_record, re.I | re.M):
                    result = 'unreachable-list'
                    break

                elif re.search(r'GTP|GPRS Tunneling Protocol|Create Session|Delete_Session|DER', error_record, re.I | re.M):
                    result = 'gtp-message-check'
                    break

                elif re.search(r'dedicated bearer', error_record, re.I | re.M):
                    result = 'dedicated-bearer-check'
                    break

                elif re.search(r'Dedicated|Bearer|generate_tft_string', error_record, re.I | re.M):
                    result = 'bearer-check'
                    break

                elif re.search(r'ike_rekey', error_record, re.I | re.M):
                    result = 'ike-rekey'
                    break

                elif re.search(r'ipsec_rekey', error_record, re.I | re.M):
                    result = 'ipsec-rekey'
                    break

                elif re.search(r'rekey', error_record, re.I | re.M):
                    result = 'rekey-check'
                    break

                elif re.search(r'statistics', error_record, re.I | re.M):
                    result = 'statistics-check'
                    break

                elif re.search(r'Echo', error_record, re.I | re.M):
                    result = 'Echo-check'
                    break

                elif re.search(r'blacklist', error_record, re.I | re.M):
                    result = 'blacklist-check'
                    break

                elif re.search(r'DNS|Domain Name System', error_record, re.I | re.M):
                    result = 'DNS-check'
                    break

                elif re.search(r'cookie', error_record, re.I | re.M):
                    result = 'cookie-check'
                    break

                elif re.search(r'Half\-Open', error_record, re.I | re.M):
                    result = 'Half-Open'
                    break

                elif re.search(r'windows\_size', error_record, re.I | re.M):
                    result = 'windows-size'
                    break

                elif re.search(r'AAA|RAR|RAA|STR|STA|code_', error_record, re.M):
                    result = 'diameter-check'
                    break

                elif re.search(r'EAP', error_record, re.I | re.M):
                    result = 'EAP-check'
                    break

                elif re.search(r'SmartDpd', error_record, re.I | re.M):
                    result = 'SmartDpd-check'
                    break

                elif re.search(r'DPD', error_record, re.I | re.M):
                    result = 'DPD-check'
                    break

                elif re.search(r'DSCP', error_record, re.I | re.M):
                    result = 'DSCP-check'
                    break

                elif re.search(r'alarm', error_record, re.I | re.M):
                    result = 'alarm-check'
                    break

                elif re.search(r'alert', error_record, re.I | re.M):
                    result = 'alert-check'
                    break

                elif re.search(r'SNMP', error_record, re.I | re.M):
                    result = 'snmp-check'
                    break

                elif re.search(r'Load Balance', error_record, re.I | re.M):
                    result = 'load-balance'
                    break

                elif re.search(r'PCSCF', error_record, re.I | re.M):
                    result = 'pcscf-check'
                    break

                elif re.search(r'swuv6', error_record, re.I | re.M):
                    result = 'swuv6-check'
                    break

                elif re.search(r'WGET', error_record, re.I | re.M):
                    result = 'wget-check'
                    break

                elif re.search(r'malicious', error_record, re.I | re.M):
                    result = 'malicious-check'
                    break

                elif re.search(r'misbehave', error_record, re.I | re.M):
                    result = 'misbehave-check'
                    break

                elif re.search(r'EBM|controlEventsReport', error_record, re.I | re.M):
                    result = 'EBM-check'
                    break

                elif re.search(r'SCTP', error_record, re.I | re.M):
                    result = 'SCTP-fail'
                    break

                elif re.search(r'mapping', error_record, re.I | re.M):
                    result = 'mapping-fail'
                    break

                elif re.search(r'data plane', error_record, re.I | re.M):
                    result = 'data-plane'
                    break

                elif re.search(r'local restart', error_record, re.I | re.M):
                    result = 'local-restart'
                    break

                elif re.search(r'failover', error_record, re.I | re.M):
                    result = 'failover-check'
                    break

                elif re.search(r'gain', error_record, re.I | re.M):
                    result = 'gain-check'
                    break

                elif re.search(r'scale_up|scale up|scale out', error_record, re.I | re.M):
                    result = 'scale-out'
                    break

                elif re.search(r'scale_down|scale down|scale in', error_record, re.I | re.M):
                    result = 'scale-in'
                    break

                elif re.search(r'PM counter', error_record, re.I | re.M):
                    result = 'pm-counter'
                    break

                elif re.search(r'pdc', error_record, re.I | re.M):
                    result = 'pdc-check'
                    break

                elif re.search(r'TLS', error_record, re.I | re.M):
                    result = 'tls-check'
                    break

                else:
                    result = 'unknow'

        return result

    def run_forever(self):
        while True:
            try:
                if self.in_queue.empty():
                    LOG.p.debug("No case need run...")
                    time.sleep(1)
                    pass
                else:
                    caseid = self.in_queue.get().strip()

                    if caseid == 'eeeeeeee':
                        while not self.out_queue.empty():
                            LOG.p.info("It time to exit, but still have results need send to server!")
                            time.sleep(1)
                        active_instance = common_tool.my_system("ps -ef |  grep -E CTS.py | grep -E -v 'grep|dtach'")
                        for old_pid in re.finditer(r'^root\s+(\d+)', active_instance, re.M):
                            LOG.p.critical("It time to exit!\nTo kill %s..." % (old_pid.group(1)))
                            common_tool.my_system("kill -9 %s" % (old_pid.group(1)))

                    self.run_case(caseid)
                    exec_id = self.get_exec_id(id=caseid)
                    if exec_id:
                        error_info_list = self.get_error_info(execid=exec_id, caseid=caseid)
                        for error_info in error_info_list:
                            LOG.p.error(str(error_info[0]))
                        result_code = self.select_result(exec_id, caseid, error_info_list)
                    else:
                        LOG.p.error("Run case fail! maybe case has errors!")
                        result_code = 'compile'
                    self.out_queue.put(caseid.strip() + '-' + result_code.strip())
                    self.result.write(caseid.strip() + ':' + result_code.strip() + '\n')
                    self.result.flush()
            except Exception as e:
                LOG.p.error("Run case end! Reason: %s" %e)
                sys.exit(0)


if __name__ == '__main__':
    pass



