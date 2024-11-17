import socket
import threading
import os


class FileServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.storage_path = "server_storage"
        self.clients = {}
        self.statistics = {
            'transfers': [],
            'response_time': []
        }

        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def start(self):
        # Start the File Server
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(6)
        print(f'Starting Server on {self.host}:{self.port}')

        while True:
            connection, address = self.server_socket.accept()
            client_thread = threading.Thread(
                target=self.handle_client,
                args=(connection, address)
            )
            client_thread.start()

    def handle_client(self, connection, address):
        # Handle Each Client Connection
        print(f'[*] Established connection from IP {address[0]} port: {address[1]}')
        while True:
            try:
                command = connection.recv(1024).decode()
                if not command:
                    break

                command_parts = command.split()
                if not command_parts:
                    continue

                operation = command_parts[0].lower()

                # Handle types of Operations
                if operation == "dir":
                    self.handle_dir(connection)
                elif operation == "upload":
                    self.handle_upload(connection, command_parts[1:])
                elif operation == "download":
                    self.handle_download(connection, command_parts[1:])
                elif operation == "delete":
                    self.handle_delete(connection, command_parts[1:])
            except Exception as ex:
                print(f'Error handling client {address}: {str(ex)}')
                break

        connection.close()
        print(f'Connection closed from IP {address[0]} port: {address[1]}')

    def handle_dir(self, connection):
        files = os.listdir(self.storage_path)
        response = '\n'.join(files)
        connection.send(response.encode())

    # Implement Later
    def handle_upload(self, connection, args):
        pass

    def handle_download(self, connection, args):
        pass

    def handle_delete(self, connection, args):
        pass