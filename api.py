from flask import Flask, request
from pathlib import Path
from io import BytesIO
import tarfile
import os

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
        return {'message': f'invalid event_id for pr {event_id}'}, 400
    if event == 'commit' and len(event_id) != 7:
        return {'message': f'invalid event_id for commit {event_id}'}, 400

    # validate namespace
    namespace = request.args.get('namespace')
    base_path = '/'
    if namespace:
        # prevent users from being able to use the parent folder '..'
        # to escape the upload www directory
        sanitized = namespace.replace(r"\.+", ".")

        # normalize namespace to construct base path
        base_path = f'/{sanitized.strip("/")}/'
        if (base_path.startswith('/pr/')
            or base_path.startswith('/commit/')
            or base_path.startswith('/api/')):
            return {'message': "invalid namespace supplied"}, 400

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

    target_path = f"{base_path}{event}/{event_id}"
    disk_path = f"www{target_path}"
    Path(disk_path).mkdir(parents=True, exist_ok=True)
    build.extractall(disk_path)
    return {
        'path': target_path,
        'url': f"https://staging.archit.us{target_path}"
    }, 200


if __name__ == '__main__':
    app.run(port=5454)
