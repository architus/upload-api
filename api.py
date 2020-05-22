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
    event_id = request.args.get('event_id')
    if not (event and event == 'pr' or event == 'commit'):
        return {'message': "missing type"}, 400
    if not event_id:
        return {'message': "missing event_id"}, 400

    tarball = BytesIO()
    while True:
        chunk = request.stream.read(4096)
        if len(chunk) == 0:
            tarball.seek(0)
            break
        tarball.write(chunk)

    try:
        build = tarfile.open(fileobj=tarball)
    except tarfile.ReadError as e:
        print(e)
        return {'message': "not a tarfile"}, 400

    Path(f"www/{event}/{event_id}").mkdir(parents=True, exist_ok=True)
    build.extractall(f"www/{event}/{event_id}")
    return {'url': f"https://staging.archit.us/{event}/{event_id}"}, 200


if __name__ == '__main__':
    app.run(port=5454)
