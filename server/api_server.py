#!/usr/bin/env python3
"""
Evolution API Server - Exposes strategy testing and evolution engine endpoints

Usage:
    python3 server/api_server.py --port 8060
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import subprocess
import threading
import time

PROJECT_DIR = Path(__file__).parent.parent
STATE_DIR = PROJECT_DIR / "evolution" / ".state"
STATE_FILE = STATE_DIR / "evolution.json"
TEST_STRATEGIES = PROJECT_DIR / "evolution" / ".state" / "test_strategies.py"

class EvolutionAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[API] {args[0]}")
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/health':
            self.send_json({"status": "ok", "timestamp": time.time()})
        
        elif path == '/state':
            try:
                with open(STATE_FILE) as f:
                    state = json.load(f)
                self.send_json(state)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        
        elif path == '/strategies':
            try:
                with open(STATE_FILE) as f:
                    state = json.load(f)
                strategies = state.get("strategies", [])
                self.send_json({"strategies": strategies})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return
        
        if path == '/heartbeat':
            self.handle_heartbeat(data)
        
        elif path == '/test-strategy':
            self.handle_test_strategy(data)
        
        elif path == '/evolve':
            self.handle_evolve(data)
        
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def handle_heartbeat(self, data):
        """Handle heartbeat task from cron job."""
        task = data.get("task", {})
        task_id = task.get("id", "unknown")
        task_type = task.get("type", "implement")
        
        print(f"[HEARTBEAT] Task: {task_id}, Type: {task_type}")
        
        if task_type == "implement":
            # Get top open issue and implement it
            result = self.implement_top_issue()
            self.send_json({"status": "ok", "task_id": task_id, "result": result})
        
        else:
            self.send_json({"error": "Unknown task type"}, 400)
    
    def handle_test_strategy(self, data):
        """Test a specific strategy."""
        strategy_id = data.get("strategy")
        cycle_num = data.get("cycle")
        
        if not strategy_id or not cycle_num:
            self.send_json({"error": "Missing strategy or cycle"}, 400)
            return
        
        try:
            result = self.run_strategy_test(strategy_id, cycle_num)
            self.send_json({"status": "ok", "result": result})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def handle_evolve(self, data):
        """Run evolution engine command."""
        command = data.get("command", "next")
        
        try:
            result = self.run_evolve_command(command)
            self.send_json({"status": "ok", "result": result})
        except Exception as e:
            self.send_json({"error": str(e)}, 500)
    
    def implement_top_issue(self):
        """Implement the top open GitHub issue."""
        try:
            # Check if strategies S002 and S003 have been tested
            with open(STATE_FILE) as f:
                state = json.load(f)
            
            strategies = {s["id"]: s for s in state.get("strategies", [])}
            
            # Check if S002 and S003 have been tested
            s002 = strategies.get("S002", {})
            s003 = strategies.get("S003", {})
            
            # Get recent cycles to see if they've been tested
            cycles = state.get("cycles", [])
            recent_strategy_tests = [c for c in cycles[-10:] if c.get("strategy") in ["S002", "S003"]]
            
            # If not recently tested, run the test
            if not recent_strategy_tests:
                # Test S002 (Content-Authority)
                print("\n=== Testing S002: Content-Authority ===")
                s002_result = self.run_strategy_test("S002", state.get("cycle", 1) + 1)
                
                # Test S003 (Referral-Engine)
                print("\n=== Testing S003: Referral-Engine ===")
                s003_result = self.run_strategy_test("S003", state.get("cycle", 1) + 2)
                
                return {
                    "s002": s002_result,
                    "s003": s003_result,
                    "message": "Successfully tested both S002 and S003 strategies"
                }
            else:
                return {
                    "message": "S002 and S003 have already been tested recently",
                    "recent_tests": recent_strategy_tests
                }
        
        except Exception as e:
            return {"error": str(e)}
    
    def run_strategy_test(self, strategy_id, cycle_num):
        """Run the strategy test module."""
        if not TEST_STRATEGIES.exists():
            raise FileNotFoundError(f"test_strategies.py not found at {TEST_STRATEGIES}")
        
        result = subprocess.run(
            [sys.executable, str(TEST_STRATEGIES), "--cycle", str(cycle_num), "--strategy", strategy_id],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise Exception(f"Test failed: {result.stderr}")
        
        # Parse the output to extract results
        output_lines = result.stdout.split('\n')
        fitness = None
        for line in output_lines:
            if "Fitness:" in line:
                fitness = float(line.split(":")[1].strip())
                break
        
        return {
            "strategy": strategy_id,
            "cycle": cycle_num,
            "fitness": fitness,
            "output": result.stdout,
            "error": result.stderr if result.stderr else None
        }
    
    def run_evolve_command(self, command):
        """Run evolution engine command."""
        result = subprocess.run(
            [sys.executable, str(PROJECT_DIR / "engine" / "evolve"), command],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        return {
            "output": result.stdout,
            "error": result.stderr if result.stderr else None,
            "returncode": result.returncode
        }

def run_server(port=8060):
    server_address = ('', port)
    httpd = HTTPServer(server_address, EvolutionAPIHandler)
    print(f"Evolution API Server running on port {port}")
    print(f"Endpoints:")
    print(f"  GET  /health - Health check")
    print(f"  GET  /state - Get current state")
    print(f"  GET  /strategies - List strategies")
    print(f"  POST /heartbeat - Handle cron heartbeat task")
    print(f"  POST /test-strategy - Test a specific strategy")
    print(f"  POST /evolve - Run evolution engine command")
    httpd.serve_forever()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Evolution API Server")
    parser.add_argument("--port", type=int, default=8060, help="Port to listen on (default: 8060)")
    args = parser.parse_args()
    
    run_server(args.port)
