from flask import Flask, request
from pathlib import Path
from io import BytesIO
import tarfile
import os
import errno

app = Flask(__name__)
key = os.environ['UPLOAD_API_KEY']


@app.route('/api/upload', methods=['POST'])
def upload():
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {key}":
        return {'message': "not authorized"}, 401

    event = request.args.get('event')
    if not (event and (event == 'pr' or event == 'commit')):
        return {'message': "missing type"}, 400

    # validate event id
    event_id = request.args.get('event_id')
    if not event_id:
        return {'message': "missing event_id"}, 400
    if event == 'pr' and not event_id.isdecimal():
        return {'message': f'invalid event_id for pr {event_id}'}
    if event == 'commit' and len(event_id) != 7:
        return {'message': f'invalid event_id for commit {event_id}'}

    # validate namespace
    namespace = request.args.get('namespace')
    base_path = '/'
    if namespace:
        # prevent users from being able to use the parent folder '..'
        # to escape the upload www directory
        sanitized = namespace.replace(r"\.+", ".")

        # normalize namespace to construct base path
        base_path = f'/{sanitized.strip('/')}/'
        if base_path.startswith('/pr/') or base_path.startswith('/commit/'):
            return {'message': "invalid namespace supplied"}

    tarball = BytesIO()
    while True:
        chunk = request.stream.read(4096)
        if len(chunk) == 0:
            tarball.seek(0)
            break
        tarball.write(chunk)

    try:
        build = tarfile.open(fileobj=tarball, mode="r:gz")
    except tarfile.ReadError as e:
        print(e)
        return {'message': "not a tarfile"}, 400

    # make sure path is valid
    target_path = f"{base_path}{event}/{event_id}"
    disk_path = f"www{target_path}"
    if not is_pathname_valid(disk_path):
        return {'message': f'invalid path "{target_path}"'}

    Path(disk_path).mkdir(parents=True, exist_ok=True)
    build.extractall(disk_path)
    return {
        'path': target_path,
        'url': f"https://staging.archit.us{target_path}"
    }, 200


# from https://stackoverflow.com/a/34102855/13192375
def is_pathname_valid(pathname: str) -> bool:
    '''
    `True` if the passed pathname is a valid pathname for the current OS;
    `False` otherwise.
    '''
    
    ERROR_INVALID_NAME = 123
    try:
        if not isinstance(pathname, str) or not pathname:
            return False
        _, pathname = os.path.splitdrive(pathname)
        root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
            if sys.platform == 'win32' else os.path.sep
        assert os.path.isdir(root_dirname)
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    except TypeError as exc:
        return False
    else:
        return True


if __name__ == '__main__':
    app.run(port=5454)
