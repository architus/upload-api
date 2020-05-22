from flask import Flask, request
from pathlib import Path
import tarfile

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    if 'build' in request.files:
        tarball = request.files['build']
        event = request.args.get('event')
        event_id = request.args.get('event_id')
        if not (event and event == 'pr' or event == 'commit'):
            return {'message': "missing type"}, 400
        if not event_id:
            return {'message': "missing event_id"}, 400

        print(tarball.filename)
        #with open(f'www/{build.filename}', 'w') as f:
        try:
            build = tarfile.open(fileobj=tarball.stream)
        except tarfile.ReadError:
            return {'message': "not a tarfile"}, 400
            #f.write(build.stream.read().decode())

        Path(f"www/{event}/{event_id}").mkdir(parents=True, exist_ok=True)
        build.extractall(f"www/{event}/{event_id}")
        print(build.list())
        return {'url': f"https://staging.archit.us/{event}/{event_id}"}, 200
    return {'message': "missing file"}, 400

if __name__ == '__main__':
        app.run()
