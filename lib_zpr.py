#!/usr/bin/env python2
"""
Check the status of zpr rsync job

This check is designed to check a file printed by the zpr_proxy user
for the output of tsp, which tracks rsync backup jobs.
"""

import pynagios
import re
from distutils.spawn import find_executable

from pynagios import Response


check_tsp_output = []
check_duplicity_out = []

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
        tspfile = '/var/lib/zpr/zpr_proxy_tsp.out'
    ):
    tspout = []
    check_host = []
    for i in open(tspfile):
        tspout.append(i.strip())
    for i in reversed(tspout):
        if re.compile('{h}$'.format(h=host)).findall(str(i).split()[-1]):
            check_host.append(i)
            break
    if check_host:
        global check_tsp_output
        check_tsp_output.append(str(check_host[0]))

def check_duplicity_job(
        jobname,
        print_output=True
    ):
    if find_executable('duplicity', path='/usr/bin'):
        if check_tsp_output:
            del check_tsp_output[0]
        if check_duplicity_out:
            del check_duplicity_out[0]
        check_tsp_out(jobname)
        if len(check_tsp_output) > 0:
            global check_duplicity_out
            split_out = check_tsp_output[0].split()
            finished = split_out[1]
            exit_code = split_out[3]
            if finished == 'finished':
                if exit_code == '0':
                    check_duplicity_out.append(
                        'Duplicity job {j} completed successfully'.format(j=jobname))
                else:
                    check_duplicity_out.append(
                        'Most recent job for {j} failed with code {e}'.format(
                            j=jobname, e=exit_code))
            else:
                check_duplicity_out.append(
                    'Duplicity job {j} is queued or running'.format(j=jobname))
        else:
            check_duplicity_out.append(
                'Duplicity job {j} is not found'.format(j=jobname))
    else:
        check_duplicity_out.append(
            'Duplicity is not configured for the specified endpoint')
    if print_output:
        if len(check_duplicity_out) > 0:
            print(check_duplicity_out[0])

if __name__ == "__main__":
    # Instantiate the plugin, check it, and then exit
    check_zpr_rsync_job(__name__)
