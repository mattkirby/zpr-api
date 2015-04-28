#!flask/bin/python
import json
import lib_zpr

from flask import Flask, jsonify, make_response


app = Flask(__name__)

api_version = 'v1.0'
api_base = str('/zpr/{v}'.format(v=api_version))

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

# @app.route('/zpr/job')
# def ls_test():
#     return json.dumps(call('ls'))

@app.route('{a}/job/<backup_host>'.format(a=api_base), methods=['GET'])
def check_job(backup_host):
    job = str(lib_zpr.check_zpr_rsync_job(backup_host))
    return json.dumps(job)

if __name__ == '__main__':
    app.run(debug=True)
