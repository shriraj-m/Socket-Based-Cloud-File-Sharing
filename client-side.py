import socket
import os
from datetime import datetime
import json


class FileClient:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        # Connect to File Server Side
        try:
            self.socket.connect((self.host, self.port))
            print(f'Connected to Server at {self.host}:{self.port}')
            return True
        except Exception as ex:
            print(f'Connection failed: {str(ex)}')
            return False

    def list_files(self):
        # Get All Files from Server
        self.socket.send("dir".encode())
        response = self.socket.recv(1024).decode()
        print("Files Currently on Server:")
        print(response)

    def upload_file(self, file_path):
        if not os.path.exists(file_path):
            print("File No Exist")
            return

        file_name = os.path.basename(file_path)
        command = f"upload {file_name}"
        # Implement

    def download_file(self, file_name):
        command = f"download {file_name}"
        # Implement

    def close(self):
        self.socket.close()

