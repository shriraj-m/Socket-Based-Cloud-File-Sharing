import socket
import os
import json
import threading
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'client_uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024
socketio = SocketIO(app, cors_allowed_origins="*")

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# HOST_IP = '34.170.82.174'  # INCLUDE BEFORE RUNNING {WILL CHANGE LATER}


class FileClient:
    def __init__(self):
        self.host = None
        self.port = None
        self.connected = False
        self.socket = None
        self.lock = threading.Lock()

    def connect(self, host='localhost', port=3300):
        # Disconnect existing connection if any
        if self.connected and self.socket:
            try:
                self.socket.close()
            except:
                pass

        # Reset connection state
        self.connected = False
        self.socket = None

        # Connect to File Server Side
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

    def ensure_connected(self):
        if not self.connected and self.host and self.port:
            self.connect(self.host, self.port)

    def list_files(self):
        with self.lock:
            try:
                # Get All Files from Server
                self.ensure_connected()
                self.socket.send("dir".encode())
                response = self.socket.recv(4096).decode()
                return True, response

            except Exception as ex:
                self.connected = False
                response = f"Failed to list files: {str(ex)}"
                return False, response

    def upload_file(self, file, overwrite=False):
        with self.lock:
            file_path = None
            try:
                self.ensure_connected()

                file_name = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)

                # Save the uploaded file temporarily
                file.save(file_path)
                file_size = os.path.getsize(file_path)

                # Send upload command with overwrite flag
                upload_command = f"upload {file_name} {'overwrite' if overwrite else ''}"
                print(f"DEBUG - Sending command: {upload_command}")
                self.socket.send(upload_command.encode())

                # Send file size
                print(f"DEBUG - Sending file size: {file_size}")
                self.socket.send(str(file_size).encode())

                # Wait for server response
                response = self.socket.recv(1024).decode()
                print(f"DEBUG - Server initial response: {response}")

                # More explicit handling of overwrite scenario
                if "confirm overwrite" in response.lower():
                    if not overwrite:
                        print("DEBUG - Overwrite required but not confirmed")
                        return False, "File exists, overwrite not confirmed"

                if any(r in response.lower() for r in ["ready", "confirm"]):
                    with open(file_path, 'rb') as f:
                        bytes_sent = 0
                        while bytes_sent < file_size:
                            chunk = f.read(4096)
                            if not chunk:
                                break
                            self.socket.send(chunk)
                            bytes_sent += len(chunk)

                            # Calculate and emit progress percentage
                            progress = (bytes_sent / file_size) * 100
                            progress = round(progress, 2)

                            # Separate progress emission from file sending
                            socketio.emit('upload_progress', {
                                'progress': progress,
                                'filename': file_name
                            })
                            print(f"DEBUG - Progress: {progress}%")

                    # Receive and clean the final response
                    self.socket.settimeout(5)  # Set a timeout to prevent hanging
                    try:
                        raw_response = self.socket.recv(1024).decode()

                        # Clean the response by removing progress-related strings
                        import re
                        final_response = re.sub(r'Progress:\d+(\.\d+)?', '', raw_response).strip()

                        print(f"DEBUG - Raw response: {raw_response}")
                        print(f"DEBUG - Cleaned final response: {final_response}")
                    except socket.timeout:
                        final_response = "Timeout waiting for server response"
                    except Exception as e:
                        final_response = f"Error receiving response: {str(e)}"

                    # Success indicators
                    success_indicators = [
                        "success",
                        "upload complete",
                        "complete",
                        "received"
                    ]

                    # Check if final response contains any success indicators
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
                print(f"Downloading to: {full_file_path}")  # Debug print

                with open(full_file_path, 'wb') as file:
                    while received_size < file_size:
                        chunk = self.socket.recv(min(4096, file_size - received_size))
                        if not chunk:
                            break
                        file.write(chunk)
                        received_size += len(chunk)

                print(f"Download complete. File size: {received_size}")  # Debug print
                return True, full_file_path
            except Exception as ex:
                print(f"Download error: {str(ex)}")  # Debug print
                self.connected = False
                return False, str(ex)

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


client = FileClient()


@app.route('/')
def index():
    return render_template('index.html',
                           connected=client.connected,
                           host=client.host,
                           port=client.port
                           )


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
        # Ensure connection is reset
        client.connected = False
        client.host = None
        client.port = None

        return jsonify({
            'success': False,
            'message': f'Connection error: {str(e)}'
        }), 500


@app.route('/list', methods=['GET'])
def list_files():
    success, response = client.list_files()
    files = response.split('\n') if success else []
    return jsonify({'success': success, 'files': files})


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

    # Handle overwrite confirmation case
    if not success and "confirm overwrite" in message.lower():
        return jsonify({
            'success': False,
            'message': message,
            'needsOverwrite': True
        })

    # Return the actual success status and message
    return jsonify({
        'success': success,
        'message': message
    })

@socketio.on('connect')
def handle_connect():
    print('Client connected to SocketIO')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected from SocketIO')


@app.route('/download/<filename>')
def download_file(filename):
    try:
        success, result = client.download_file(filename)
        print(f"Download result: {success}, Path: {result}")  # Debug print

        if success and os.path.exists(result):
            return send_file(result, as_attachment=True, download_name=filename)
        else:
            print(f"Download failed for {filename}")  # Debug print
            return f"File {filename} not found", 404
    except Exception as e:
        print(f"Download exception: {str(e)}")  # Debug print
        return f"Download failed: {str(e)}", 500


@app.route('/delete/<filename>', methods=['DELETE'])  # Changed to DELETE method
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


# Add error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'success': False,
        'message': 'File too large'
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)
