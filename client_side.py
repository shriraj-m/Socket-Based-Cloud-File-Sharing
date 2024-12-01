import socket
import os
import re
import threading
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit

# Creates a flask app. 
app = Flask(__name__)
# Defines an upload folder for the client side.
app.config['UPLOAD_FOLDER'] = 'client_uploads'
# Defines the maximum content length for the upload folder.
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024
# Creates a socketio object for the app.
socketio = SocketIO(app, cors_allowed_origins="*")
# Creates the upload folder if it doesn't exist.
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Class that contains all methods for the client side.
class FileClient:
    def __init__(self):
        self.host = None
        self.port = None
        self.connected = False
        self.socket = None
        self.lock = threading.Lock()

    # Method to connect to the server.
    def connect(self, host='localhost', port=3300):
        if self.connected and self.socket:
            try:
                self.socket.close()
            except:
                pass

        # Reset connection state
        self.connected = False
        self.socket = None

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            self.host = host
            self.port = port
            print(f'[*] Connected to Server at {self.host}:{self.port}')
            return True

        except Exception as ex:
            print(f'Connection failed: {str(ex)}')
            self.host = None
            self.port = None
            return False
        
    # Method to ensure that the client is connected to the server.
    def ensure_connected(self):
        if not self.connected and self.host and self.port:
            self.connect(self.host, self.port)

    # Method to list all files in the server.
    def list_files(self):
        with self.lock:
            try:
                self.ensure_connected()
                self.socket.send("dir".encode())
                response = self.socket.recv(4096).decode()
                return True, response

            except Exception as ex:
                self.connected = False
                response = f"Failed to list files: {str(ex)}"
                return False, response

    # Method to upload a file to the server.
    def upload_file(self, file, overwrite=False):
        with self.lock:
            file_path = None
            try:
                self.ensure_connected()

                file_name = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)

                file.save(file_path)
                file_size = os.path.getsize(file_path)

                upload_command = f"upload {file_name} {'overwrite' if overwrite else ''}"
                print(f"DEBUG - Sending command: {upload_command}")
                if overwrite:
                    self.socket.send('yes'.encode())
                self.socket.send(upload_command.encode())

                response = self.socket.recv(1024).decode()
                print(f"DEBUG - Server initial response: {response}")

                print(f"DEBUG - Sending file size: {file_size}")
                self.socket.send(str(file_size).encode())

                response = self.socket.recv(1024).decode()
                print(f"DEBUG - Server initial response: {response}")

                if response == "File Exists. Overwrite? (Yes/No): ":
                    if overwrite:
                        print(f"DEBUG - YES OVERWRITE: {response}")
                        self.socket.send('yes'.encode())
                    else:
                        return False, "File Exists."

                if any(r in response.lower() for r in ["ready", "confirm"]):
                    with open(file_path, 'rb') as f:
                        bytes_sent = 0
                        while bytes_sent < file_size:
                            chunk = f.read(4096)
                            if not chunk:
                                break
                            self.socket.send(chunk)
                            bytes_sent += len(chunk)

                            progress = (bytes_sent / file_size) * 100
                            progress = round(progress, 2)

                            socketio.emit('upload_progress', {
                                'progress': progress,
                                'filename': file_name
                            })
                            print(f"DEBUG - Progress: {progress}%")

                    self.socket.settimeout(5)  
                    try:
                        raw_response = self.socket.recv(1024).decode()
                        final_response = re.sub(r'Progress:\d+(\.\d+)?', '', raw_response).strip()

                        print(f"DEBUG - Raw response: {raw_response}")
                        print(f"DEBUG - Cleaned final response: {final_response}")
                    except socket.timeout:
                        final_response = "Timeout waiting for server response"
                    except Exception as e:
                        final_response = f"Error receiving response: {str(e)}"

                    success_indicators = [
                        "success",
                        "upload complete",
                        "complete",
                        "received"
                    ]

                    upload_successful = (
                            any(indicator in final_response.lower() for indicator in success_indicators)
                            or bytes_sent == file_size
                    )

                    if upload_successful:
                        print("DEBUG - Upload successful")
                        return True, "File uploaded successfully"
                    else:
                        print(f"DEBUG - Upload potentially failed: {final_response}")
                        return False, f"Upload failed: {final_response}"

                print(f"DEBUG - Unexpected server response: {response}")
                return False, f"Unexpected server response: {response}"

            except Exception as ex:
                print(f"DEBUG - Upload error: {str(ex)}")
                self.connected = False
                return False, f"Upload failed: {str(ex)}"
            finally:
                if file_path and os.path.exists(file_path):
                    try:
                        os.unlink(file_path)
                    except Exception as e:
                        print(f"WARNING: Failed to delete temporary file: {e}")

    # Method to download a file from the server.
    def download_file(self, file_name):
        with self.lock:
            try:
                self.ensure_connected()
                self.socket.send(f"download {file_name}".encode())

                response = self.socket.recv(1024).decode()
                if response == "File not found":
                    return False, response

                file_size = int(response)
                self.socket.send("Ready".encode())

                received_size = 0
                full_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
                print(f"Downloading to: {full_file_path}")  

                with open(full_file_path, 'wb') as file:
                    while received_size < file_size:
                        chunk = self.socket.recv(min(4096, file_size - received_size))
                        if not chunk:
                            break
                        file.write(chunk)
                        received_size += len(chunk)

                print(f"Download complete. File size: {received_size}")  
                return True, full_file_path
            except Exception as ex:
                print(f"Download error: {str(ex)}")  
                self.connected = False
                return False, str(ex)
            
    # Method to delete a file from the server.
    def delete_file(self, file_name):
        with self.lock:
            try:
                self.ensure_connected()
                self.socket.send(f"delete {file_name}".encode())
                response = self.socket.recv(1024).decode()
                return True, response
            except Exception as ex:
                self.connected = False
                response = f"Delete Failed: {str(ex)}"
                return False, response

    def close(self):
        self.socket.close()

# Creates a client object to be used in the flask app.
client = FileClient()

# Route to render the index.html file.
@app.route('/')
def index():
    return render_template('index.html',
                           connected=client.connected,
                           host=client.host,
                           port=client.port
                           )

# Route to connect to the server.
@app.route('/connect', methods=['POST'])
def connect():
    try:
        data = request.get_json()
        host = data.get('host', 'localhost')
        port = data.get('port', 3300)

        # Explicitly close any existing connection
        if client.connected and client.socket:
            try:
                client.socket.close()
            except:
                pass

        success = client.connect(host, port)

        message = f'Connected to Server at {client.host}:{client.port}' if success else 'Connection failed'
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400
    except Exception as e:
        client.connected = False
        client.host = None
        client.port = None

        return jsonify({
            'success': False,
            'message': f'Connection error: {str(e)}'
        }), 500

# Route to list all files in the server.
@app.route('/list', methods=['GET'])
def list_files():
    success, response = client.list_files()
    files = response.split('\n') if success else []
    return jsonify({'success': success, 'files': files})

# Route to upload a file to the server.
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'})

    file = request.files['file']
    overwrite = request.form.get('overwrite', 'false').lower() == 'true'

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})

    print(f"DEBUG - Attempting to upload file: {file.filename} (overwrite: {overwrite})")
    success, message = client.upload_file(file, overwrite)

    print(f"DEBUG - Upload result - Success: {success}, Message: {message}")

    if not success and "confirm overwrite" in message.lower():
        return jsonify({
            'success': False,
            'message': message,
            'needsOverwrite': True
        })

    return jsonify({
        'success': success,
        'message': message
    })

# SocketIO event to handle connection.
@socketio.on('connect')
def handle_connect():
    print('Client connected to SocketIO')

# SocketIO event to handle disconnection.
@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from SocketIO')

# Route to download a file from the server.
@app.route('/download/<filename>')
def download_file(filename):
    try:
        success, result = client.download_file(filename)
        print(f"Download result: {success}, Path: {result}")  

        if success and os.path.exists(result):
            return send_file(result, as_attachment=True, download_name=filename)
        else:
            print(f"Download failed for {filename}")  
            return f"File {filename} not found", 404
    except Exception as e:
        print(f"Download exception: {str(e)}")  
        return f"Download failed: {str(e)}", 500

# Route to delete a file from the server.
@app.route('/delete/<filename>', methods=['DELETE'])  
def delete_file(filename):
    try:
        success, message = client.delete_file(filename)
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Delete failed: {str(e)}'
        }), 500

# Error handler for internal server error.
@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)
