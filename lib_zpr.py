#!/usr/bin/env python2
"""
Check the status of zpr rsync job

This check is designed to check a file printed by the zpr_proxy user
for the output of tsp, which tracks rsync backup jobs.
"""

import re
import os
import datetime

from subprocess import check_output


check_tsp_output = []
check_tsp_job_out = []
check_job_changes = []
json_output = []

def check_tsp_out(
        host,
        check=1
    ):
    os.environ['TMPDIR'] = '/var/lib/zpr/task_spooler'
    tspout = []
    check_host = []
    for i in check_output('tsp').split('\n'):
        tspout.append(i)
    for i in reversed(tspout):
        if i != '':
            name = i.split()[-1].split('/')[-1]
            if re.compile('^{h}$'.format(h=host)).findall(name):
                if check > len(check_host):
                    check_host.append(i)
                else:
                    break
    if len(check_host) > 0:
        global check_tsp_output
        if check_tsp_output:
            del check_tsp_output[0:]
        for i in check_host:
            check_tsp_output.append(i)

def check_tsp_job(
        jobname,
        check=1,
        print_output=False,
        show_changes=False
    ):
    global check_tsp_job_out
    global check_job_changes
    global json_output
    if check_tsp_output:
        del check_tsp_output[0:]
    if check_tsp_job_out:
        del check_tsp_job_out[0:]
    if show_changes:
        del check_job_changes[0:]
    if json_output:
        del json_output[0:]
    check_tsp_out(jobname, check)
    executable = []
    if len(check_tsp_output) > 0:
        for i in check_tsp_output:
            job_results = {}
            job_results['name'] = jobname
            split_out = i.split()
            finished = split_out[1]
            tmp_file_mtime = os.path.getmtime(split_out[2])
            mtime = datetime.datetime.fromtimestamp(tmp_file_mtime).strftime('%Y-%m-%d %H:%M:%S')
            job_results['time_completed'] = mtime
            exit_code = split_out[3]
            job_results['exit_code'] = exit_code
            if re.compile('/usr/bin/duplicity').findall(check_tsp_output[0]):
                executable = 'duplicity'
            elif re.compile('/usr/bin/rsync').findall(check_tsp_output[0]):
                executable = 'rsync'
            else:
                exit(1)
            job_results['job_type'] = executable
            if finished == 'finished':
                if show_changes:
                    changes = []
                    for i in open(split_out[2]):
                        changes.append(i.strip())
                    if changes:
                        check_job_changes.append(changes)
                        job_results['output'] = changes
                if exit_code == '0':
                    check_tsp_job_out.append(
                        '{x} job {j} completed successfully at {m}'.format(
                            x=executable, j=jobname, m=mtime))
                    job_results['result'] = 'successful'
                else:
                    check_tsp_job_out.append(
                        '{x} job for {j} failed with code {e} at {m}'.format(
                            x=executable, j=jobname, e=exit_code, m=mtime))
                    job_results['result'] = 'fail'
            else:
                check_tsp_job_out.append(
                    '{x} job {j} is queued or running'.format(x=executable, j=jobname))
            json_output.append(job_results)
    else:
        check_tsp_job_out.append(
            'job {j} is not found'.format(j=jobname))
    if print_output:
        if len(check_tsp_job_out) > 0:
            for i in check_tsp_job_out:
                print(i)
                if show_changes:
                    if len(check_job_changes) >= check_tsp_job_out.index(i):
                        print('\n'.join(check_job_changes[check_tsp_job_out.index(i)]))

if __name__ == "__main__":
    # Instantiate the plugin, check it, and then exit
    check_tsp_job(__name__)
