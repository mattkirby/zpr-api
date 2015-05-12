#!/var/lib/zpr/api/bin/python
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

@app.route('{a}/job/<backup_host>'.format(a=api_base), methods=['GET'])
def check_zpr_job(backup_host):
    lib_zpr.check_tsp_job(backup_host)
    return json.dumps(str(lib_zpr.check_tsp_job_out[0]))

@app.route('{a}/job/<backup_host>/output'.format(a=api_base), methods=['GET'])
def check_zpr_job_summary(backup_host):
    lib_zpr.check_tsp_job(backup_host, show_changes=True)
    job_checked = [
        {
            'name': backup_host,
            'response': lib_zpr.check_tsp_job_out[0],
            'changes': lib_zpr.check_job_changes
        }
    ]
    return jsonify({'job_checked': job_checked})

    #return json.dumps(join_summary, indent=2)

if __name__ == '__main__':
#   formatter = logging.Formatter(\
#       "%(asctime)s - %(levelname)s - %(name)s: \t%(messages)s")
#   handler.setFormatter(formatter)
    app.run(debug=True, extra_files='/var/lib/zpr/api/lib_zpr.py')
