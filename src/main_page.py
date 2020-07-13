import os
import flask
import pywps

import set_project_root_dir
set_project_root_dir.set_project_root_dir()  # call this before import processes

import processes

# This is, how you start PyWPS instance
config_files = ['./data/static/config/pywps.cfg']
service = pywps.Service(processes=processes.processes, cfgfiles=config_files)

main_page = flask.Blueprint('main_page', __name__, template_folder='templates')


# return 'hello to the WPS server root'
@main_page.route('/wps', methods=['GET', 'POST'])
def wps():
    return service


@main_page.route('/test')
def test():
    return 'hello test!'


@main_page.route("/")
def hello():
    server_url = pywps.configuration.get_config_value("server", "url")
    request_url = flask.request.url
    return flask.render_template('home.html', request_url=request_url,
                                 server_url=server_url,
                                 process_descriptor=processes.process_descriptor)


def flask_response(targetfile):
    if os.path.isfile(targetfile):
        with open(targetfile, mode='rb') as f:
            file_bytes = f.read()
        file_ext = os.path.splitext(targetfile)[1]
        mime_type = 'text/xml' if 'xml' in file_ext else None
        return flask.Response(file_bytes, content_type=mime_type)
    else:
        flask.abort(404)


@main_page.route('/outputs/' + '<path:filename>')
def outputfile(filename):
    targetfile = os.path.join('outputs', filename)
    return flask_response(targetfile)


@main_page.route('/data/' + '<path:filename>')
def datafile(filename):
    targetfile = os.path.join('data', filename)
    return flask_response(targetfile)


# not sure how the static route works. static route doesn't reach this function.
@main_page.route('/static/' + '<path:filename>')
def staticfile(filename):
    targetfile = os.path.join('static', filename)
    return flask_response(targetfile)
