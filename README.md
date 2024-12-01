# Socket-Based Cloud File Sharing

A client-server program / application that enables file sharing over a network using socket programming in Python. This project also features a web-based user interface for easy file management.

## Features

- **Real-time File Transfer**: Upload and download files with progress tracking
- **Web Interface**: Clean and responsive UI built with Flask
- **File Management**: 
  - List files stored on the server
  - Upload files with overwrite protection
  - Download files to local storage
  - Delete files from server
- **Network Statistics**: Track and log transfer rates, file sizes, and operation durations. The stats are saved on the server side.
- **Connection Management**: Automatic reconnection handling and connection status monitoring
- **Multi-threaded Server**: Supports multiple concurrent client connections

## Tech Stack

- **Backend**:
  - Python
  - Flask
  - Socket Programming
  - Flask-SocketIO
- **Frontend**:
  - HTML5
  - CSS3
  - JavaScript
  - Axios for HTTP requests
  - Socket.IO for real-time communication

## Client Side Project Structure
- Socket-Based-Cloud-File-Sharing/
  - ├── client_side.py 
  - ├── static/
  - │ └── styles.css 
  - ├── templates/
  - │ └── index.html 
  - ├── client_uploads/

## Server Side Project Structure
├── server_side.py 
├── statistics_collector.py 
├── network_statistics.json
├── server_storage/


## Setup and Usage
1. Decide where to set up server_side. Whether it is in the cloud or on a seperate pc.
2. Host server_side.py by running it (python3 server_side.py)
3. Host client_side.py by running it (python client_side.py)
4. client_side.py displays accessible web interface at localhost:5001
5. On web interface, grab external address and input it to connect to the server. 
6. Upload file from personal computer
7. Refresh (if needed) and your file is there!
8. [Optional] Download file!
9. [Optional] Stop server and view network_statistics.json to see the stats of the actions/files.


## Contributions
This application acts as a final project for CNT3004 | COMPUTER NETWORKS @ Florida Polytechinc University and was completed by:
@shrirajm
@alexmeert
@ianlopez07
@mndecormier
