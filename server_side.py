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
        try:
            files = os.listdir(self.storage_path)
            file_info = []

            for file_name in files:
                file_path = os.path.join(self.storage_path, file_name)
                size = os.path.getsize(file_path)
                modified = os.path.getmtime(file_path)
                # Only include the filename without additional metadata
                file_info.append(file_name)  # Changed this line

            response = "\n".join(file_info) if file_info else "No Files Found"
            connection.send(response.encode())

        except Exception as ex:
            print(f"Directory listing error: {str(ex)}")
            connection.send(f"Directory listing failed: {str(ex)}".encode())

    # Implement Later
    def handle_upload(self, connection, args):
        pass

    def handle_download(self, connection, file_name):
        try:
            file_path = os.path.join(self.storage_path, file_name)
            if not os.path.exists(file_path):
                connection.send("File not found".encode())
                return

            file_size = os.path.getsize(file_path)
            connection.send(str(file_size).encode())

            if connection.recv(1024).decode() != "Ready":
                return

            start_time = datetime.now()
            size = 0

            with open(file_path, 'rb') as file:
                while True:
                    chunk = file.read(4096)
                    if not chunk:
                        break
                    connection.send(chunk)
                    size += len(chunk)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            transfer_rate = (file_size / (1024 * 1024)) / duration
            network_stats = Network_Statistics()
            network_stats.transfer_stats(
                'upload',
                file_name,
                size,
                duration,
                transfer_rate
            )
        except Exception as ex:
            connection.send(f"Download Failed: {str(ex)}".encode())

    def handle_delete(self, connection, file_name):
        try:
            file_path = os.path.join(self.storage_path, file_name)

            if not os.path.exists(file_path):
                connection.send("File not found".encode())
                return

            os.remove(file_path)
            connection.send("File deleted successfully".encode())

        except Exception as ex:
            print(f"Delete error: {str(ex)}")
            connection.send(f"Delete failed: {str(ex)}".encode())


if __name__ == '__main__':
    server = FileServer()
    server.start()