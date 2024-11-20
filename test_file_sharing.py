# test_file_sharing.py
import os
import time
import threading
import unittest
from server_side import *
from client_side import *

class TestFileSharing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create test directories
        cls.test_server_dir = "test_server_storage"
        cls.test_client_dir = "test_client_storage"
        cls.server_host = 'localhost'
        cls.server_port = 5000

        # Create test directories if they don't exist
        for directory in [cls.test_server_dir, cls.test_client_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Create test files
        cls.create_test_files()

        # Start server in a separate thread
        cls.server = FileServer(host=cls.server_host, port=cls.server_port)
        cls.server_thread = threading.Thread(target=cls.server.start)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # Give server time to start
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        # Clean up test files and directories
        cls.cleanup_test_files()

    @classmethod
    def create_test_files(cls):
        """Create test files of different sizes"""
        # Create a small text file (1 KB)
        with open(os.path.join(cls.test_client_dir, "test_small.txt"), "w") as f:
            f.write("A" * 1024)

        # Create a medium text file (1 MB)
        with open(os.path.join(cls.test_client_dir, "test_medium.txt"), "w") as f:
            f.write("B" * (1024 * 1024))

        # Create a larger text file (5 MB)
        with open(os.path.join(cls.test_client_dir, "test_large.txt"), "w") as f:
            f.write("C" * (5 * 1024 * 1024))

    @classmethod
    def cleanup_test_files(cls):
        """Clean up test files and directories"""
        for directory in [cls.test_server_dir, cls.test_client_dir]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        print(f"Error deleting {file_path}: {e}")
                os.rmdir(directory)

    def setUp(self):
        """Set up for each test"""
        self.client = FileClient(host=self.server_host, port=self.server_port)
        self.client.connect()

    def tearDown(self):
        """Clean up after each test"""
        self.client.close()

    def test_connection(self):
        """Test basic connection to server"""
        client = FileClient(host=self.server_host, port=self.server_port)
        self.assertTrue(client.connect())
        client.close()

    def test_list_files(self):
        """Test directory listing"""
        self.client.list_files()
        # Initially directory should be empty
        response = self.client.list_files()
        self.assertEqual(response.strip(), "")

    def test_upload_small_file(self):
        """Test uploading a small file"""
        filename = "test_small.txt"
        filepath = os.path.join(self.test_client_dir, filename)
        self.client.upload_file(filepath)

        # Verify file exists in server directory
        server_filepath = os.path.join(self.test_server_dir, filename)
        self.assertTrue(os.path.exists(server_filepath))

        # Verify file contents
        with open(filepath, 'rb') as f1, open(server_filepath, 'rb') as f2:
            self.assertEqual(f1.read(), f2.read())

    def test_upload_and_download(self):
        """Test uploading and then downloading a file"""
        filename = "test_medium.txt"
        upload_path = os.path.join(self.test_client_dir, filename)
        download_path = os.path.join(self.test_client_dir, "downloaded_" + filename)

        # Upload file
        self.client.upload_file(upload_path)

        # Download file
        self.client.download_file(filename, download_path)

        # Verify downloaded file matches original
        with open(upload_path, 'rb') as f1, open(download_path, 'rb') as f2:
            self.assertEqual(f1.read(), f2.read())

    def test_delete_file(self):
        """Test deleting a file"""
        filename = "test_small.txt"
        filepath = os.path.join(self.test_client_dir, filename)

        # Upload file first
        self.client.upload_file(filepath)

        # Delete file
        self.client.delete_file(filename)

        # Verify file is deleted from server
        server_filepath = os.path.join(self.test_server_dir, filename)
        self.assertFalse(os.path.exists(server_filepath))

    def test_concurrent_connections(self):
        """Test multiple clients connecting simultaneously"""
        num_clients = 3
        clients = []

        # Create and connect multiple clients
        for _ in range(num_clients):
            client = FileClient(host=self.server_host, port=self.server_port)
            self.assertTrue(client.connect())
            clients.append(client)

        # Clean up
        for client in clients:
            client.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)