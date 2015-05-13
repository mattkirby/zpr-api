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

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('{a}/job/<backup_host>/last'.format(a=api_base), methods=['GET'])
def check_last_zpr_job(backup_host):
    lib_zpr.check_tsp_job(backup_host)
    return jsonify({'job_result': lib_zpr.json_output})

@app.route('{a}/job/<backup_host>/last/<int:count>'.format(a=api_base), methods=['GET'])
def check_last_count_zpr_job(backup_host, count):
    lib_zpr.check_tsp_job(backup_host, count)
    return jsonify({'job_result': lib_zpr.json_output})

@app.route('{a}/job/<backup_host>/output'.format(a=api_base), methods=['GET'])
def check_zpr_job_summary(backup_host):
    lib_zpr.check_tsp_job(backup_host, show_changes=True)
    return jsonify({'job_result': lib_zpr.json_output})

@app.route('{a}/job/<backup_host>/output/<int:count>'.format(a=api_base), methods=['GET'])
def check_zpr_job_summary_count(backup_host, count):
    lib_zpr.check_tsp_job(backup_host, count, show_changes=True)
    return jsonify({'job_result': lib_zpr.json_output})

@app.route('{a}/job/<backup_host>/last/nagios'.format(a=api_base), methods=['GET'])
def check_zpr_job_last_nagios(backup_host):
    lib_zpr.check_zpr_rsync_nagios(backup_host)
    result = [
        {
            'nagios_return': str(lib_zpr.json_output[0].get('nagios_return')),
            'exit_code': lib_zpr.json_output[0].get('exit_code')
        }
    ]
    return jsonify({'job_result': result})

if __name__ == '__main__':
#   formatter = logging.Formatter(\
#       "%(asctime)s - %(levelname)s - %(name)s: \t%(messages)s")
#   handler.setFormatter(formatter)
    app.run(debug=True, extra_files='/var/lib/zpr/api/lib_zpr.py')
