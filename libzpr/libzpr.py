#!/usr/bin/env python2
"""
Serialize data from task spooler, gather system data and ship to elasticsearch

This library will help gather data from task spooler and help
send it to elasticsearch, or return json.
"""

import re
import os
import sys
import pytz

from datetime import datetime, timedelta
from subprocess import check_output
from elasticsearch import Elasticsearch
from socket import getfqdn


class Tsp:
    """
    Gather data from task spooler and send it away
    """

    def __init__(self):
        self.output = []
        self.results = []
        self.toremove = []

    def get_output(self, search=None, status='finished'):
        """
        Get output from taskspooler about finished jobs
        """
        tspout = check_output('tsp').split('\n')
        for i in tspout[1:-1]:
            if i:
                if i.split()[1] == status:
                    if search:
                        if re.compile(search).findall(i):
                            self.output.append(i.split())
                    else:
                        self.output.append(i.split())

    def get_results(self):
        """
        Gather exit code and job file for a tsp job
        """
        for i in self.output:
            results = {}
            toremove = {}
            index = self.output[self.output.index(i)]
            if re.compile('/.*').findall(index[2]):
                tspfile = index[2]
            times = index[4].split('/')
            toremove['tspid'] = index[0]
            results['title'] = index[-1].split('/')[-1]
            results['worker'] = getfqdn()
            results['exit_code'] = index[3]
            results['time'] = self.get_timestamp(tspfile)
            results['primary_storage'] = self.check_nfs_source(results['title'])
            results['job_time_seconds'] = times[0]
            results['user_cpu'] = times[1]
            results['system_cpu'] = times[2]
            if tspfile:
                toremove['tspfile'] = tspfile
                tspfile = toremove['tspfile']
                if os.path.isfile(tspfile):
                    results['changes'] = self.read_file(tspfile)
                    err_file = str('{}.e'.format(tspfile))
                    if os.path.isfile(err_file):
                        results['errors'] = self.read_file(err_file)
            snapdir = str('/srv/backup/{}/.zfs/snapshot'.format(results['title']))
            if os.path.exists(snapdir):
                results['snapshots'] = os.listdir(snapdir)
            jobfile = self.read_file('{}/.ssh/permitted_commands/{}'.format(os.path.expanduser('~'), results['title']))
            results['job_type'] = self.get_job_type(jobfile)
            results['host_url'] = self.get_target_fqdn(jobfile)
            self.results.append(results)
            self.toremove.append(toremove)
        self.check_if_changes()

    @staticmethod
    def get_job_type(title):
        """
        Determine the job type based on command content
        """
        if re.compile('/usr/bin/duplicity').findall(str(title)):
            if re.compile('remove-older-than').findall(str(title)):
                return 'duplicity_cleanup'
            elif re.compile('full-if-older-than').findall(str(title)):
                return 'duplicity'
        elif re.compile('/usr/bin/rsync').findall(str(title)):
            return 'rsync'

    def check_if_changes(self, out='changes', err='errors'):
        """
        Checks for content in changes and errors. Populates has_changes / has_errors
        """
        for i in self.results:
            if not i.get(out) == None: # Check if there are any changes
                if i[out] == []:
                    i['has_{}'.format(out)] = False
                    del i[out]
                else:
                    i['has_{}'.format(out)] = True
            if not i.get(err) == None:
                if i[err] == []:
                    i['has_{}'.format(err)] = False
                    del i[err]
                else:
                    i['has_{}'.format(err)] = True
            else:
                if i['exit_code'] == '0':
                    i['has_{}'.format(err)] = False
                else:
                    i['has_{}'.format(err)] = True

    @staticmethod
    def is_dst(zonename):
        """
        Check if it is daylight savings now
        """
        tz = pytz.timezone(zonename)
        now = pytz.utc.localize(datetime.utcnow())
        return now.astimezone(tz).dst() != timedelta(0)

    def get_timestamp(self, filename, zonename='America/Los_Angeles'):
        """
        Get a formated timestamp of the last modified time of a file
        """
        file_mtime = os.path.getmtime(filename)
        time_format = '%Y-%m-%dT%H:%M:%S'
        mtime = datetime.fromtimestamp(file_mtime).strftime(time_format)
        if self.is_dst(zonename):
            zone = '-0700'
        else:
            zone = '-0800'
        return str('{}{}'.format(mtime, zone))

    @staticmethod
    def read_file(filename):
        """
        Get the output of a file and return a list
        """
        file_out = []
        for i in open(filename):
            file_out.append(i.strip())
        return file_out

    @staticmethod
    def check_nfs_source(title):
        """
        Checks /etc/fstab for source of a nfs mount
        """
        for i in open('/etc/fstab'):
            if re.compile(title).findall(i):
                if re.compile('^{}$'.format(title)).findall(i.split()[1].split('/')[-1]):
                    return i.split(':')[0]

    @staticmethod
    def get_target_fqdn(source, user='zpr_proxy'):
        """
        Get the fqdn of the job target
        """
        for i in source:
            if re.compile('^{}@'.format(user)).findall(i):
                return i.split('@')[-1].split(':')[0]

    @staticmethod
    def remove_task(taskid):
        """
        Remove a job from the taskspooler list
        """
        check_output(['tsp', '-r', taskid])

    @staticmethod
    def send_to_elasticsearch(
            content,
            index='zpr',
            doc='zpr_job',
            url='elasticsearch.ops.puppetlabs.net',
            esid=None
        ):
        """
        Send results to elasticsearch in the specified index
        """
        es = Elasticsearch([{'host': url, 'port': 9200}])
        if es.ping():
            es.index(index, doc, content, id=esid)
        else:
            sys.exit(1)

    @staticmethod
    def list_files(startpath):
        """
        List a file tree in json
        """
        tree = []
        for root, dirs, files in os.walk(startpath):
            root_list = {'directory': '{}/'.format(os.path.basename(root))}
            file_list = []
            for filename in files:
                file_list.append(filename)
            root_list['files'] = file_list
            tree.append(root_list)
        return tree
