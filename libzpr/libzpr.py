#!/usr/bin/env python2
"""
Serialize data from task spooler, gather system data and ship to elasticsearch

This library will help gather data from task spooler and help
send it to elasticsearch, or return json.
"""

import re
import os
import shutil
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
        tspout = check_output('/usr/bin/tsp').split('\n')
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
            results['title'] = self.find_title(index)
            job_filename = '{}/.ssh/permitted_commands/{}'.format(os.path.expanduser('~zpr_proxy'), results['title'])
            if os.path.exists(job_filename):
                jobfile = self.read_file(job_filename)
                snapdir = '/srv/backup/{}/.zfs/snapshot'.format(results['title'])
                results['primary_storage'] = self.check_nfs_source(results['title'])
                if os.path.exists(snapdir):
                    results['snapshots'] = os.listdir(snapdir)
            else:
                jobfile = index
            results['job_type'] = self.get_job_type(jobfile)
            results['worker'] = getfqdn()
            results['exit_code'] = index[3]
            results['time'] = self.get_timestamp(tspfile)
            line_timestamp = re.compile(r'time=\d+').findall(str(index))
            if line_timestamp:
                results['time_queued'] = self.get_timestamp(timestamp=float(line_timestamp[0]))
            results['job_time_seconds'] = times[0]
            results['user_cpu'] = times[1]
            results['system_cpu'] = times[2]
            nfsdir = '/srv/backup/{}_job_results'.format(results['worker'])
            if tspfile:
                toremove['tspfile'] = tspfile
                if os.path.isfile(tspfile):
                    results['changes'] = self.return_file_contents(tspfile)
                    if os.path.getsize(tspfile) > 500000:
                        results['truncate_output'] = True
                        self.copy_to_nfs(nfsdir, tspfile, '{}/{}_{}'.format(nfsdir, results['title'], results['time']))
                    err_file = '{}.e'.format(tspfile)
                    if os.path.isfile(err_file):
                        results['errors'] = self.return_file_contents(err_file)
                        if os.path.getsize(err_file) > 500000:
                            self.copy_to_nfs(nfsdir, tspfile, '{}/{}_{}.e'.format(nfsdir, results['title'], results['time']))
            results['host_url'] = self.get_target_fqdn(jobfile)
            self.results.append(results)
            self.toremove.append(toremove)
        self.check_if_changes()

    @staticmethod
    def get_job_type(title):
        """
        Determine the job type based on command content
        """
        if 'run_duplicity' in str(title):
            return 'duplicity'
        elif '/usr/bin/rsync' in str(title):
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

    def get_timestamp(self, filename=None, timestamp=None, zonename='America/Los_Angeles'):
        """
        Get a formated timestamp of the last modified time of a file
        """
        if filename:
            source_time = os.path.getmtime(filename)
        if timestamp:
            source_time = timestamp
        time_format = '%Y-%m-%dT%H:%M:%S'
        mtime = datetime.fromtimestamp(source_time).strftime(time_format)
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

    def read_and_truncate(self, filename, lines):
        """
        Get the number of lines requested from the end of a file
        """
        trunc_out = []
        file_out = self.read_file(filename)
        count_lines = 0
        for i in reversed(file_out):
            count_lines = count_lines + 1
            if count_lines > lines:
                break
            trunc_out.append(i)
        trunc_out.sort(reverse=True)
        return trunc_out

    def return_file_contents(self, filename, lines=1000, maxsize=500000):
        """
        Return requested file contents. If larger than .5MB truncate the file
        """
        if os.path.getsize(filename) > maxsize:
            file_out = self.read_and_truncate(filename, lines)
        else:
            file_out = self.read_file(filename)
        return file_out

    @staticmethod
    def copy_to_nfs(nfs, srcfile, destfile):
        """
        Check if destination is nfs, then copy file
        """
        if os.path.ismount(nfs):
            shutil.copyfile(srcfile, destfile)
        else:
            print '{} is not a nfs mount'.format(nfs)
            sys.exit(1)

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
        if len(source) > 1:
            look = source
        else:
            look = source[0].split()
        for i in look:
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
            print 'Cannot reach elasticsearch at {}'.format(url)
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

    @staticmethod
    def find_title(source_list):
        """
        Find the title of a job
        """
        if 'run_duplicity' in source_list[8]:
            return source_list[9].split('/')[-1]
        for i in reversed(source_list):
            if not re.compile(';|time=').findall(i):
                return i.split('/')[-1]
