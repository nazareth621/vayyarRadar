""" example code for EVK client """
from struct import unpack_from
import json
import numpy as np
from websocket import create_connection

DTYPES = {
    0: np.int8,
    1: np.uint8,
    2: np.int16,
    3: np.uint16,
    4: np.int32,
    5: np.uint32,
    6: np.float32,
    7: np.float64,
}

ASCII_RS = '\u001e'
ASCII_US = '\u001f'


def to_message(buffer):
    """ parse MatNet messages from JSON / Vayyar internal binary format """
    if isinstance(buffer, str):
        return json.loads(buffer)
    seek = 0
    fields_len = unpack_from('i', buffer, seek + 4)[0]
    fields_split = unpack_from(str(fields_len) + 's', buffer, seek + 8)[0].decode('utf8').split(ASCII_RS)
    msg = {'ID': fields_split[0], 'Payload':
dict.fromkeys(fields_split[1].split(ASCII_US))}
    seek += 8 + fields_len
    for key in msg['Payload']:
        seek += np.int32().nbytes
        dtype = DTYPES[np.asscalar(np.frombuffer(buffer, np.int32, 1, seek))]
        seek += np.int32().nbytes
        ndims = np.asscalar(np.frombuffer(buffer, np.int32, 1, seek))
        seek += np.int32().nbytes
        dims = np.frombuffer(buffer, np.int32, ndims, seek)
        seek += ndims * np.int32().nbytes
        data = np.frombuffer(buffer, dtype, np.prod(dims), seek)
        seek += np.prod(dims) * dtype().nbytes
        msg['Payload'][key] = data.reshape(dims) if ndims else np.asscalar(data)
    return msg

def main():
    # """ connect to server and echoing messages """
    listener = create_connection("ws://127.0.0.1:1234/")
    # retrieve current configuration
    listener.send(json.dumps({
        'Type': 'COMMAND',
        'ID': 'SET_PARAMS',
        'Payload': {
            'Cfg.MonitoredRoomDims': [-0.1, 2, 0.5, 3, 0.2, 1.8],# Room dimensions
            'Cfg.Common.sensorOrientation.mountPlane':'xz',#xy - ceiling, xz - wall
            'Cfg.Common.sensorOrientation.transVec[3]': [1.8],# Height of sensor
            'Cfg.imgProcessing.substractionMode':6, #6-AMTI,7-MTI,2-Initial,0-NS.
            'MPR.save_dir': r'', # Saved records directory
            'MPR.read_from_file': 0.0, # 1 – To play records
            'MPR.save_to_file': 0.0, # 1 – To save raw data
            'MPR.save_image_to_file': 0.0, # 1 – To save image data
        }
    }))

    # set outputs for each frame
    listener.send(json.dumps({
        'Type': 'COMMAND',
        'ID': 'SET_OUTPUTS',
        'Payload': {
            'binary_outputs': ['I', 'Q', 'pairs', 'freqs' ,'rawImage_XYZ', 'rawImage_XY', 'rawImage_XZ', 'rawImage_YZ'],
        }
    }))

    # start the engine - only if WebGUI isn't present
    listener.send(json.dumps({
        'Type': 'COMMAND',
        'ID': 'START',
        'Payload': {}
    }))

    # request for binary data. Can also request 'JSON_DATA' if 'json_outputs' were specified
    listener.send(json.dumps({'Type': 'QUERY', 'ID': 'BINARY_DATA'}))
    print("Running! Waiting for messages...")
    while True:
        buffer = listener.recv()
        data = to_message(buffer)
        print(data['ID'])
        if data['ID'] == 'BINARY_DATA':
            # data['Payload'] is now available to use
            print("pairs:")
            print(data['Payload']['pairs'])
            print("freqs:")
            print(data['Payload']['freqs'])
            print("I[0]:")
            print(data['Payload']['I'][0, 0])
            print("Q[0]:")
            print(data['Payload']['Q'][0, 0])
            print("rawImage_XYZ:")
            print(data['Payload']['rawImage_XYZ'])
            print("rawImage_XY:")
            print(data['Payload']['rawImage_XY'])
            print("rawImage_XZ:")
            print(data['Payload']['rawImage_XZ'])
            print("rawImage_YZ:")
            print(data['Payload']['rawImage_YZ'])
            listener.send(json.dumps({'Type': 'QUERY', 'ID': 'BINARY_DATA'}))
        if data['ID'] == 'GET_STATUS':
            print(data['Payload']['status'])
        if data['ID'] == 'SET_PARAMS':
            print("CONFIGURATION:")
            for key in data['Payload']:
                print(key, data['Payload'][key])
    listener.close()

    if name == 'main':
        main()