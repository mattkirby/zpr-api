#!bin/python
import json
import lib_zpr
import logging

from flask import Flask, jsonify, make_response, abort


app = Flask(__name__)

api_version = 'v1.0'
api_base = str('/zpr/{}'.format(api_version))

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('{a}/job/<backup_host>/last'.format(a=api_base), methods=['GET'])
def check_last_zpr_job(backup_host):
    lib_zpr.check_tsp_job(backup_host)
    if lib_zpr.json_output:
        return jsonify({'job_result': lib_zpr.json_output})
    else:
        abort(404)

@app.route('{a}/job/<backup_host>/last/<int:count>'.format(a=api_base), methods=['GET'])
def check_last_count_zpr_job(backup_host, count):
    lib_zpr.check_tsp_job(backup_host, count)
    if lib_zpr.json_output:
        return jsonify({'job_result': lib_zpr.json_output})
    else:
        abort(404)

@app.route('{a}/job/<backup_host>/last/output'.format(a=api_base), methods=['GET'])
def check_zpr_job_summary(backup_host):
    lib_zpr.check_tsp_job(backup_host, show_changes=True)
    if lib_zpr.json_output:
        return jsonify({'job_result': lib_zpr.json_output})
    else:
        abort(404)

@app.route('{a}/job/<backup_host>/last/output/<int:count>'.format(a=api_base), methods=['GET'])
def check_zpr_job_summary_count(backup_host, count):
    lib_zpr.check_tsp_job(backup_host, count, show_changes=True)
    if lib_zpr.json_output:
        return jsonify({'job_result': lib_zpr.json_output})
    else:
        abort(404)

@app.route('{a}/job/<backup_host>/files'.format(a=api_base), methods=['GET'])
def check_zpr_files(backup_host):
    lib_zpr.list_files('/srv/backup/{}'.format(backup_host))
    if lib_zpr.json_output:
        return jsonify({'files': lib_zpr.json_output})
    else:
        abort(404)

if __name__ == '__main__':
    app.run(debug=True, extra_files='/var/lib/zpr/api/lib_zpr.py')
