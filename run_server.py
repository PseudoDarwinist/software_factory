#!/usr/bin/env python3
"""
Simple HTTP server to test the Software Factory website locally.
Run this script and it will automatically find an available port.
"""

import http.server
import socketserver
import os
import socket

# Change to the directory containing the HTML file
os.chdir('/Users/chetansingh/Documents/AI_Project/Software_Factory')

def find_free_port():
    """Find a free port starting from 8000"""
    for port in range(8000, 8100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

PORT = find_free_port()

if PORT is None:
    print("Could not find a free port between 8000-8099")
    exit(1)

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Server running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.shutdown()