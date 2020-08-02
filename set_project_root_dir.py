import os


def set_project_root_dir():
    new_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    os.chdir(new_root)
    print('root path: {}:'.format(os.getcwd()))

