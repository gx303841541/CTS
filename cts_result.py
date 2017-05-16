#!/usr/bin/env python3
import psycopg2 as psycopg
import datetime, os, sys, time, re, getopt
import cprint
import configparser
import fcntl
from subprocess import *


#file lock
def file_lock(open_file):
    return fcntl.flock(open_file, fcntl.LOCK_EX | fcntl.LOCK_NB)


def file_unlock(open_file):
    return fcntl.flock(open_file, fcntl.LOCK_UN)  


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


def sys_init():
    global p
    p = cprint.cprint('')
    p.notice_p("Start...\n")


    global db 
    db = result()

    try:
        opts, args = getopt.getopt(sys.argv[1:], "c:d:e:hm", ["help", 'execid', 'caseid', 'merge', 'dir'])
    except getopt.GetoptError as err:
        p.error_p(str(err)) # will print something like "option -a not recognized"
        help_info()
        sys.exit(2)

    global dir_name
    dir_name = '.'

    global exec_id
    exec_id = ''

    global case_id
    case_id = ''


    global task_list
    task_list = []
    
    for opt, value in opts:
    
        if opt in ("-c", '--caseid'):
            case_id = value   
            
        elif opt in ("-d", '--dir'):
            dir_name = value
            task_list.append([db.get_result_by_dir, value])
        
        elif opt in ("-e", '--execid'):
            exec_id = value
            task_list.append([get_error_by_id])
                
        elif opt in ("-h", "--help"):
            task_list.append([help_info])
            break

        elif opt in ("-m", "--merge"):
            tmp_dir = os.path.dirname(args[0])
            if len(tmp_dir):
                dir_name = tmp_dir
            task_list.append([db.result_merge, args])

        else:
            assert False, "unhandled option: opt"
            help_info()
            sys.exit(2)   


class result():
    def __init__(self, host = "127.0.0.1", user = 'postgres', password = '', db = "Wireless_3G", port = 5432):
        cxn = psycopg.connect(database=db, user=user, password=password, host=host, port=port)
        cur = cxn.cursor()
        self.cxn = cxn
        self.cur = cur

    def get_daily_result(self, day = 0, start_time = '21:00:00', end_time = '09:00:00'):
        today = datetime.date.today()
        end_day = today - datetime.timedelta(days = day)
        start_day = today - datetime.timedelta(days = (day + 1))
        
        time_now = datetime.datetime.now()
        now_time = time_now.strftime('%H:%M:%S')

        print("SELECT id, exec_date from executionids where exec_date between timestamp '%s' AND timestamp '%s';" % (str(start_day) + ' ' + str(start_time), str(end_day) + ' ' + str(end_time)))
        self.cur.execute("SELECT id, exec_date from executionids where exec_date between timestamp '%s' AND timestamp '%s';" % (str(start_day) + ' ' + str(start_time), str(end_day) + ' ' + str(end_time)));
        execid_list = []
        for i in self.cur.fetchall():
            execid_list.append(i[0])
        execid_list.sort()


        #self.cur.execute("SELECT min(execution_id) from results where testcase_id=%s and execution_id>=%s;" % ('10002051', execid_list[0]))
        self.cur.execute("SELECT min(execution_id) from results where execution_id>=%s;" % (execid_list[0]))
        if self.cur.fetchall():
            print("Yes!")
        else:
            print("No!")
            return 0

        self.cur.execute("SELECT testcase_id,execution_id,level,result from results where execution_id>=%s;" % (execid_list[0]))
        execid_caseid_level_result = {}
        for i in self.cur.fetchall():
            execid_caseid_level_result[i[1]] = [i[0], i[2], i[3]] 
            self.cur.execute("SELECT error from errors where execution_id=%s and testcase_id=%s;" % (i[1], i[0]));
            for j in self.cur.fetchall():
                print(j)
                break


    def get_error_by_id(self, execid, caseid):
        result = []
        self.cur.execute("SELECT error from errors where execution_id=%s and testcase_id=%s;" % (execid, caseid));
        for i in self.cur.fetchall():
            result.append(i)

        return result


    def get_result_by_dir(self, dir):        
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
            p.notice_p("Create cts.result done!\n")
        else:
            p.warning_p("No result for %s" % dir)


    def result_judge(self, exec_id, case_id, error_list):

        result = 'NONE'


        self.cur.execute("SELECT result from results where execution_id=%s and testcase_id=%s and level=2;" % (exec_id, case_id));
        for i in self.cur.fetchall():
            v, *o = i
            if v == 1:
                result = 'pass'


        if len(error_list):
            for record in error_list:
                error_record = str(record)
                if re.search(r'Crashfile found', error_record, re.I | re.M):
                    result = 'crash-found'
                    break

                elif re.search(r'no memory name|memory check failed|ListPool check fail|DumpRegion check fail', error_record, re.I | re.M):
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
                    #break

        #p.nitice_p(result)
        return result


    def result_maker(self, result_show):
        if len(result_show):
            my_system_no_check("rm -rf %s/cts.result" % (dir_name))
            result_file = open("%s/cts.result" % (dir_name), 'w')
            for item in sorted(result_show):
                #p.notice_p("%s VS %s" % (item, result_show[item]))
                result_file.write("%s=%s\n" % (item, result_show[item]))

            result_file.close()
            
        else:
            p.error_p("No result!")  
    

    def result_merge(self, result_list):  
        #('24889', '81942024')=pass

        stastics_by_case = {}
        stastics_by_error = {}

        if len(result_list):
            for file in result_list:
                for line in open(file, 'r'):
                    r = re.match(r"\('(?P<execid>\d+)', '(?P<caseid>(?P<ffd>\d{4})\d+)'\)=(?P<result>[\w-]+)", line, re.M)

                    if r:
                        pass
                    else:
                        p.error_p(line)   

                    if r.group('ffd') in stastics_by_case:
                        if r.group('caseid') in stastics_by_case[r.group('ffd')]:
                            if stastics_by_case[r.group('ffd')][r.group('caseid')] == 'pass':
                                continue
                            elif r.group('result') == 'pass':
                                stastics_by_case[r.group('ffd')][r.group('caseid')] = 'pass'
                                stastics_by_case[r.group('ffd')]['pass'] += 1

                        else:
                            stastics_by_case[r.group('ffd')][r.group('caseid')] = r.group('result')
                            stastics_by_case[r.group('ffd')]['total'] += 1                            
                            if r.group('result') == 'pass':
                                stastics_by_case[r.group('ffd')]['pass'] += 1

                    else:
                        stastics_by_case[r.group('ffd')] = {}
                        stastics_by_case[r.group('ffd')]['total'] = 0
                        stastics_by_case[r.group('ffd')]['pass'] = 0
                        stastics_by_case[r.group('ffd')][r.group('caseid')] = r.group('result')
                        stastics_by_case[r.group('ffd')]['total'] += 1
                        if r.group('result') == 'pass':
                            stastics_by_case[r.group('ffd')]['pass'] += 1


            
            for ffd in stastics_by_case:
                for caseid in stastics_by_case[ffd]:
                    error = stastics_by_case[ffd][caseid]

                    if error == 'pass' or re.match(r'total|pass', caseid, re.I):
                        continue
                    
                    if error in stastics_by_error:
                        if ffd in stastics_by_error[error]:
                            stastics_by_error[error][ffd] += 1
                            stastics_by_error[error]['total'] += 1

                        else:
                            stastics_by_error[error][ffd] = 0
                            
                            stastics_by_error[error][ffd] += 1
                            stastics_by_error[error]['total'] += 1

                    else:
                        stastics_by_error[error] = {}
                        stastics_by_error[error][ffd] = 0
                        stastics_by_error[error]['total'] = 0
                        
                        stastics_by_error[error][ffd] += 1
                        stastics_by_error[error]['total'] += 1


            #if len(stastics_by_error):
            if True:
                my_system_no_check("rm -rf %s/result.log" % (dir_name))
                #time.sleep(5)
                total_result_file = open("%s/result.log" % (dir_name), 'w')
            
                total_pass = 0
                total_cases = 0
                for ffd in stastics_by_case:
                    total_pass += stastics_by_case[ffd]['pass']
                    total_cases += stastics_by_case[ffd]['total']

                    if stastics_by_case[ffd]['pass'] != stastics_by_case[ffd]['total']:
                        #total_result_file.write("FFD%s: %s/%s(fail/total)\n" % (ffd, stastics_by_case[ffd]['total'] - stastics_by_case[ffd]['pass'], stastics_by_case[ffd]['total']))
                        total_result_file.write("FFD%s: %s\n" % (ffd, stastics_by_case[ffd]['total'] - stastics_by_case[ffd]['pass']))
                    else:
                        continue

                    counter = 0
                    max_counter = 2000
                    for caseid in stastics_by_case[ffd]:
                        if stastics_by_case[ffd][caseid] != 'pass' and not re.match(r'total|pass', caseid, re.I) and counter <= max_counter:
                            if counter < max_counter:
                                counter += 1
                                total_result_file.write("\t%s:%s\n" % (caseid, stastics_by_case[ffd][caseid]))
                            else:
                                total_result_file.write("\t......\n")
                                break

                    total_result_file.write('-' * 40 + '\n')

                #total_result_file.write("\nTotal: %s/%s(fail/total)\n" % (total_cases - total_pass, total_cases))
                total_result_file.write("\nTotal: %s\n" % (total_cases - total_pass))


                total_result_file.write('\n' + '=' * 80 + '\n\n')



                total_fail = 0
                for error_info in stastics_by_error:
                    total_fail += stastics_by_error[error_info]['total']

                    total_result_file.write("%s: %s\n" % (error_info, stastics_by_error[error_info]['total']))

                    for ffd in stastics_by_error[error_info]:
                        if not re.match(r'total', ffd, re.I):
                            total_result_file.write("\t%s: %s\n" % (ffd, stastics_by_error[error_info][ffd]))

                    total_result_file.write('-' * 40 + '\n')

                total_result_file.write("\nTotal: %s\n" % (total_fail))

                total_result_file.close()
                p.notice_p("Create result.log done!\n")

        else:
            p.warning_p("No result file!") 



def help_info():
    help_info = '''
This is a tool to get cts result:                 
        -c          --case ID

        -d          --dir when result is, such as: '/opt/cts_log/regression-20170108-2128/'
                    -d /opt/cts_log/regression-20170108-2128/

        -e          --exec ID
                    -e 123 -c 81920001

        -h          --show you what you are reading now, wakakakaka~
        
        -m          --merge are results
                    -m *.result                                                    
    '''    
    
    for line in help_info.split('\n'):
        if re.search(r'\w\s{5,}-', line, re.M):
            p.notice_p(line)
        else:
            if not re.match(r'^\s*$', line, re.M):
                p.warning_p(line)
     
        

def get_error_by_id():

    counter = 0
    if len(exec_id) and len(case_id):
        result = db.get_error_by_id(exec_id, case_id)
        for i in result:
            counter += 1
            print("%d:\n" % (counter))
            p.common_p("%s\n\n" % (i), fore='red')

        p.notice_p("result:%s" % (db.result_judge(exec_id, case_id, result)))
    else:
        p.warning_p("Both exec id and case id should be given!")



        
def sys_schedule():
    for task in task_list:
        handle = task.pop(0)
        if len(task):
            handle(*task)
        else:
            handle()


def sys_exit():
    p.notice_p('\nHappy time always so fast, it is time to say good bye!')


def map_ffd():
    try:
        import xlrd
        
        d = {}
        wb = xlrd.open_workbook('/opt/cts/CTS/ssr_epdg/regression_cases/script/others/FFD_Mapping.xlsx')
        sh = wb.sheet_by_index(0)
        for i in range(sh.nrows):
            ffd = str(int(sh.cell(i, 0).value))
            feature = sh.cell(i, 1).value
            d[ffd]  = feature
            

        f_tmp = open('result.log', 'rU')
            
        content = f_tmp.read()

        for k,v in d.items():
            content = content.replace('FFD'+k, v)

        log_date = datetime.datetime.now().strftime("%m%d%H%M")
        f = open('result_analysed_%s.log'%log_date, 'w')
        f.write(content)

    except Exception as e:
        print("Internal Error, Reason: %s" %e)

if __name__ == '__main__':

    sys_init()
    
    sys_schedule()

    map_ffd()

    sys_exit()
