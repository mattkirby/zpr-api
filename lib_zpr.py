#!/usr/bin/env python2
"""
Check the status of zpr rsync job

This check is designed to check a file printed by the zpr_proxy user
for the output of tsp, which tracks rsync backup jobs.
"""

import pynagios
import re
import os
import datetime

from subprocess import check_output
from pynagios import Response


check_tsp_output = []
check_tsp_job_out = []
check_job_changes = []

def check_zpr_rsync_job(backup_host):
    tspfile = '/var/lib/zpr/zpr_proxy_tsp.out'
    tspout = []
    check_host = []
    for i in open(tspfile):
        tspout.append(i.strip())
    for i in reversed(tspout):
        if re.compile(backup_host).findall(i):
            check_host.append(i)
            break

    if not check_host:
        return Response(pynagios.UNKNOWN, 'Cannot find host matching {h}'.format(h=backup_host))

    c_exit = str(check_host[0]).split()[3]

    if c_exit == '0':
        return Response(pynagios.OK,
                        "Most recent zpr backup job for %s has run successfully." % backup_host)
    elif c_exit == '23':
        e_23 = [
            "Last zpr backup job for {e} has returned exit code 23.".format(e=c_exit),
            'This is usually because of an IO error due to permission being denied',
            'to read a file, or because of a file being deleted after the job started.',
            'You may consider adding ignore-errors to the job.',
        ]
        return Response(pynagios.WARNING, ' '.join(e_23))
    elif c_exit == '12':
        e_12 = [
            str("Last zpr backup job for {host}".format(host=backup_host)),
            'has failed with exit code 12',
            'because the ssh key for zpr_user was denied.',
        ]
        return Response(pynagios.CRITICAL, ' '.join(e_12))
    elif c_exit != '0':
        return Response(pynagios.CRITICAL,
                        "Last zpr backup job for %s has failed with exit code %s." % (
                            backup_host, c_exit))

def check_tsp_out(
        host,
        check=1
    ):
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
    if check_tsp_output:
        del check_tsp_output[0:]
    if check_tsp_job_out:
        del check_tsp_job_out[0:]
    if show_changes:
        del check_job_changes[0:]
    check_tsp_out(jobname, check)
    executable = []
    if len(check_tsp_output) > 0:
        for i in check_tsp_output:
            split_out = i.split()
            finished = split_out[1]
            tmp_file_mtime = os.path.getmtime(split_out[2])
            mtime = datetime.datetime.fromtimestamp(tmp_file_mtime).strftime('%Y-%m-%d %H:%M:%S')
            exit_code = split_out[3]
            if re.compile('/usr/bin/duplicity').findall(check_tsp_output[0]):
                executable = 'duplicity'
            elif re.compile('/usr/bin/rsync').findall(check_tsp_output[0]):
                executable = 'rsync'
            else:
                exit(1)
            if finished == 'finished':
                if show_changes:
                    changes = []
                    for i in open(split_out[2]):
                        changes.append(i.strip())
                    if changes:
                        check_job_changes.append(changes)
                if exit_code == '0':
                    check_tsp_job_out.append(
                        '{x} job {j} completed successfully at {m}'.format(
                            x=executable, j=jobname, m=mtime))
                else:
                    check_tsp_job_out.append(
                        '{x} job for {j} failed with code {e} at {m}'.format(
                            x=executable, j=jobname, e=exit_code, m=mtime))
            else:
                check_tsp_job_out.append(
                    '{x} job {j} is queued or running'.format(x=executable, j=jobname))
    else:
        check_tsp_job_out.append(
            'job {j} is not found'.format(j=jobname))
    if print_output:
        if len(check_tsp_job_out) > 0:
            for i in check_tsp_job_out:
                print(i)
                if show_changes:
                    if len(check_job_changes) >= check_tsp_job_out.index(i):
                        print(check_job_changes[check_tsp_job_out.index(i)])

if __name__ == "__main__":
    # Instantiate the plugin, check it, and then exit
    check_zpr_rsync_job(__name__)
