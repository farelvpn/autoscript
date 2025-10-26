#!/usr/bin/env python3
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import subprocess
import json
import os
import threading
import time
import signal
import sys
import select
import termios
import tty
from urllib.parse import urlparse

# Setup logging - systemd akan menangani log output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Systemd akan capture stdout
    ]
)

# Read API tokens from file
try:
    with open('/etc/api/key', 'r') as token_file:
        valid_tokens = [line.strip() for line in token_file if line.strip()]
    logging.info(f"Loaded {len(valid_tokens)} API tokens")
except FileNotFoundError:
    logging.error("Token file /etc/api/key not found")
    valid_tokens = []
except Exception as e:
    logging.error(f"Error reading token file: {e}")
    valid_tokens = []

# Thread-safe counter for active connections
class ConnectionCounter:
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()
        self._shutdown = False
    
    def increment(self):
        with self._lock:
            if self._shutdown:
                return False
            self._count += 1
            return True
    
    def decrement(self):
        with self._lock:
            self._count -= 1
    
    def get_count(self):
        with self._lock:
            return self._count
    
    def start_shutdown(self):
        with self._lock:
            self._shutdown = True
            return self._count

# Global connection counter
connection_counter = ConnectionCounter()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads"""
    daemon_threads = True
    allow_reuse_address = True
    timeout = 30
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_shutting_down = False
    
    def shutdown(self):
        """Graceful shutdown - wait for active connections to complete"""
        self._is_shutting_down = True
        active_connections = connection_counter.start_shutdown()
        logging.info(f"Shutdown initiated. Waiting for {active_connections} active connections to complete...")
        
        # Wait for active connections to complete with timeout
        timeout = 30  # 30 seconds max wait
        start_time = time.time()
        while connection_counter.get_count() > 0 and (time.time() - start_time) < timeout:
            time.sleep(0.5)
            remaining = connection_counter.get_count()
            if remaining > 0 and (time.time() - start_time) % 5 < 1:
                logging.info(f"Waiting for {remaining} connections to complete...")
        
        if connection_counter.get_count() > 0:
            logging.warning(f"Forcing shutdown with {connection_counter.get_count()} active connections")
        else:
            logging.info("All connections completed, shutting down")
        
        super().shutdown()

class RequestHandler(BaseHTTPRequestHandler):
    timeout = 60
    protocol_version = 'HTTP/1.1'
    
    def handle(self):
        """Override handle to track active connections"""
        if not connection_counter.increment():
            self.send_error(503, "Server is shutting down")
            return
        
        try:
            super().handle()
        except Exception as e:
            logging.error(f"Error handling request: {e}")
        finally:
            connection_counter.decrement()
    
    def log_message(self, format, *args):
        """Override log_message to use our logging"""
        logging.info(f"{self.client_address[0]} - {format % args}")
    
    def log_request_info(self, additional_info=''):
        client_ip = self.client_address[0]
        user_agent = self.headers.get('User-Agent', 'User-Agent not provided')
        thread_name = threading.current_thread().name
        logging.info(f'IP: {client_ip}, Path: {self.path}, Thread: {thread_name}, {additional_info}')

    def do_AUTHHEAD(self):  
        self.send_response(401)  
        self.send_header('WWW-Authenticate', 'Bearer realm="Authentication required"')  
        self.send_header('Content-type', 'application/json')  
        self.end_headers()  
        self.wfile.write(b'{"message": "Unauthorized: Missing or invalid Bearer token"}')  
        self.log_request_info('Unauthorized access attempt')  

    def authorize(self):  
        auth_header = self.headers.get('Authorization')  
        if not auth_header or not auth_header.startswith('Bearer '):  
            self.do_AUTHHEAD()  
            return False  

        provided_token = auth_header[7:].strip()  
        if provided_token not in valid_tokens:  
            self.do_AUTHHEAD()  
            return False  
        return True  

    def execute_script(self, script_path, post_data=None):  
        if not os.path.isfile(script_path):  
            self.send_response(404)  
            self.send_header('Content-type', 'application/json')  
            self.end_headers()  
            self.wfile.write(b'{"error": "Script not found"}')  
            self.log_request_info(f'Script not found: {script_path}')  
            return  

        try:  
            env = os.environ.copy()
            env['REQUEST_METHOD'] = self.command
            env['PATH_INFO'] = self.path
            
            if post_data:  
                result = subprocess.run(
                    [script_path], 
                    input=post_data, 
                    capture_output=True, 
                    text=True, 
                    check=True,
                    timeout=30,
                    env=env
                )  
            else:  
                result = subprocess.run(
                    [script_path], 
                    capture_output=True, 
                    text=True, 
                    check=True,
                    timeout=30,
                    env=env
                )  
            
            self.send_response(200)  
            self.send_header('Content-type', 'application/json')  
            self.end_headers()  
            self.wfile.write(result.stdout.encode())  
            self.log_request_info(f'Script executed: {script_path}')  
            
        except subprocess.CalledProcessError as e:  
            self.send_response(500)  
            self.send_header('Content-type', 'application/json')  
            self.end_headers()  
            error_message = json.dumps({
                "error": f"Script execution failed", 
                "details": str(e),
                "stderr": e.stderr[:500] if e.stderr else "No error output"
            })  
            self.wfile.write(error_message.encode())  
            self.log_request_info(f'Script error: {script_path}')  
            logging.error(f'Script execution error: {e.stderr}')  
        except subprocess.TimeoutExpired:  
            self.send_response(504)  
            self.send_header('Content-type', 'application/json')  
            self.end_headers()  
            error_message = json.dumps({"error": "Script execution timeout"})  
            self.wfile.write(error_message.encode())  
            self.log_request_info(f'Script timeout: {script_path}')  
        except Exception as e:  
            self.send_response(500)  
            self.send_header('Content-type', 'application/json')  
            self.end_headers()  
            error_message = json.dumps({"error": f"Unexpected error: {str(e)}"})  
            self.wfile.write(error_message.encode())  
            self.log_request_info(f'Unexpected error: {script_path}')  
            logging.error(f'Unexpected script error: {e}')  

    def do_GET(self):  
        if not self.authorize():  
            return
        
        parsed_path = urlparse(self.path)
        script_name = parsed_path.path.lstrip('/')
        
        if not script_name:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "No script specified"}')
            return
            
        self.execute_script(f'/usr/local/sbin/api/{script_name}')  

    def do_POST(self):  
        if not self.authorize():  
            return  
        
        content_length = int(self.headers.get('Content-Length', 0))  
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else None
        
        parsed_path = urlparse(self.path)
        script_name = parsed_path.path.lstrip('/')
        
        if not script_name:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "No script specified"}')
            return
            
        self.execute_script(f'/usr/local/sbin/api/{script_name}', post_data)  

    def do_DELETE(self): 
        self.do_POST()  
    
    def do_PUT(self): 
        self.do_POST()  
    
    def do_PATCH(self): 
        self.do_POST()  
    
    def do_OPTIONS(self):  
        if not self.authorize():  
            return  
        self.send_response(200)  
        self.send_header('Allow', 'GET, POST, DELETE, PUT, PATCH, OPTIONS')  
        self.send_header('Content-type', 'application/json')  
        self.end_headers()  
        self.wfile.write(b'{"message": "OPTIONS request received"}')  
        self.log_request_info()

# Global server instance
httpd = None
shutting_down = False

def signal_handler(signum, frame):
    global shutting_down
    if shutting_down:
        return
        
    shutting_down = True
    signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
    logging.info(f"Received {signal_name}, initiating graceful shutdown...")
    
    if httpd:
        def shutdown_server():
            httpd.shutdown()
            logging.info("Server shutdown completed")
        
        shutdown_thread = threading.Thread(target=shutdown_server)
        shutdown_thread.daemon = True
        shutdown_thread.start()

def is_terminal():
    """Check if running in terminal"""
    return sys.stdin.isatty()

def keyboard_listener():
    """Listen for keyboard input (q to quit) when running in terminal"""
    if not is_terminal():
        return
        
    print("\nWebAPI Server started. Press 'q' then Enter to stop, Ctrl+C to immediate shutdown")
    print("=" * 60)
    
    # Save original terminal settings
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        tty.setraw(sys.stdin.fileno())
        
        while not shutting_down:
            # Check for input with timeout
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1)
                if key.lower() == 'q':
                    print("\nReceived 'q' command, initiating graceful shutdown...")
                    signal_handler(signal.SIGINT, None)
                    break
                    
    except Exception as e:
        logging.debug(f"Keyboard listener error: {e}")
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def display_status():
    """Display server status when running in terminal"""
    if not is_terminal():
        return
        
    def status_monitor():
        while not shutting_down:
            active_connections = connection_counter.get_count()
            status_msg = f"\rActive connections: {active_connections} | Press 'q' to quit"
            sys.stdout.write(status_msg)
            sys.stdout.flush()
            time.sleep(1)
    
    monitor_thread = threading.Thread(target=status_monitor, daemon=True)
    monitor_thread.start()

def main():
    global httpd
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    port = 9000
    server_address = ('', port)
    
    try:
        # Create threaded server
        httpd = ThreadedHTTPServer(server_address, RequestHandler)
        
        # Start keyboard listener if in terminal
        if is_terminal():
            kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
            kb_thread.start()
            display_status()
        
        logging.info(f'🚀 WebAPI Server Proxy starting on port {port}')
        logging.info(f'📊 Process ID: {os.getpid()}')
        logging.info(f'🐍 Python version: {sys.version.split()[0]}')
        logging.info(f'📁 Working directory: {os.getcwd()}')
        logging.info(f'🔑 Loaded {len(valid_tokens)} API tokens')
        logging.info('✅ Server is ready to accept connections')
        
        if is_terminal():
            logging.info("💡 Running in terminal mode - Press 'q' to quit gracefully")
        
        # Serve forever
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received")
    except Exception as e:
        logging.error(f'Server error: {e}')
        sys.exit(1)
    finally:
        logging.info('👋 Server has been shut down')
        if is_terminal():
            print("\n" + "=" * 50)
            print("WebAPI Server has been stopped")
            print("Thank you for using WebAPI Server Proxy!")

if __name__ == "__main__":
    main()
