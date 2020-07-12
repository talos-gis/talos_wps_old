import flask

from main_page import main_page

app = flask.Flask(__name__)
app.register_blueprint(main_page)

