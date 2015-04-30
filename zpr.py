#!bin/python
import json
import lib_zpr
#import logging
#from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, make_response


app = Flask(__name__)

# app.logger.setLevel(logging.INFO)
# app.logger.disabled = False
# handler = logging.handlers.RotatingFileHandler(
#     '/var/log/zpr_flask.log',
#     'a',
#     maxBytes=1024 * 1024 * 100,
#     backupCount=20
#     )
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.DEBUG)
# app.logger.addHandler(handler)

api_version = 'v1.0'
api_base = str('/zpr/{v}'.format(v=api_version))
extra_files = [ '/var/lib/zpr/api/lib_zpr.py', '/var/lib/zpr/api/zpr.py' ]

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

# @app.route('/zpr/job')
# def ls_test():
#     return json.dumps(call('ls'))

# @app.route('{a}/job/rsync/<backup_host>'.format(a=api_base), methods=['GET'])
# def check_job(backup_host):
#     job = str(lib_zpr.check_zpr_rsync_job(backup_host))
#     return json.dumps(job)

@app.route('{a}/job/rsync/<backup_host>'.format(a=api_base), methods=['GET'])
def check_rsync_job(backup_host):
    lib_zpr.check_tsp_job(
        executable='rsync',
        jobname=backup_host
        )

@app.route('{a}/job/duplicity/<backup_host>'.format(a=api_base), methods=['GET'])
def check_offsite_job(backup_host):
    lib_zpr.check_tsp_job(
        executable='duplicity',
        jobname=backup_host
        )

if __name__ == '__main__':
#   formatter = logging.Formatter(\
#       "%(asctime)s - %(levelname)s - %(name)s: \t%(messages)s")
#   handler.setFormatter(formatter)
    app.run(host='127.0.0.1', extra_files=':'.join(extra_files))
