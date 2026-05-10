"""Model Context Protocol (MCP) Client for Zotero Integration."""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from .db import Database

logger = logging.getLogger(__name__)

import subprocess
import threading
import queue
import time
import uuid

logger = logging.getLogger(__name__)

class ZoteroMCPClient:
    """
    Client for interacting with the external Zotero MCP Server via stdio.
    Provides tools for the Citation Verifier to ground hallucinated references.
    """
    
    def __init__(self, repo_root: Optional[Path] = None, server_path: Optional[str] = None):
        self.repo_root = repo_root
        self.server_path = server_path
        self.connected = False
        self._tools = []
        self._db: Optional[Database] = None
        
        self._process: Optional[subprocess.Popen] = None
        self._response_queues: Dict[str, queue.Queue] = {}
        self._reader_thread: Optional[threading.Thread] = None
        self.on_tool_call: Any = None
        
        if repo_root:
            self._db = Database(repo_root)
        
    def connect(self) -> bool:
        """Establish connection to the MCP Server via stdio."""
        if self.connected:
            return True
            
        if not self.server_path:
            logger.info("No Zotero MCP server path provided. Defaulting to MOCK mode.")
            self._tools = self._get_mock_tools()
            self.connected = True
            return True
            
        try:
            logger.info(f"Launching MCP Server: {self.server_path}")
            # Launch the server process
            self._process = subprocess.Popen(
                self.server_path,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start background reader thread
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
            
            # 1. Initialize MCP Handshake
            init_id = str(uuid.uuid4())
            self._send_request(init_id, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "RuWritingStyles", "version": "1.0.0"}
            })
            
            # Wait for initialize response (timeout 5s)
            self._wait_for_response(init_id, timeout=5)
            
            # 2. Discover Tools
            list_id = str(uuid.uuid4())
            self._send_request(list_id, "tools/list", {})
            list_resp = self._wait_for_response(list_id, timeout=5)
            
            self._tools = list_resp.get("tools", [])
            self.connected = True
            logger.info(f"Connected to MCP Server. Discovered {len(self._tools)} tools.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to real MCP Server: {e}. Falling back to MOCK.")
            self._tools = self._get_mock_tools()
            self.connected = True
            return False

    def _read_loop(self):
        """Background thread to read JSON-RPC messages from the server's stdout."""
        while self._process and self._process.poll() is None:
            line = self._process.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line)
                if "id" in msg:
                    msg_id = str(msg["id"])
                    if msg_id in self._response_queues:
                        self._response_queues[msg_id].put(msg)
                elif "method" in msg:
                    # Handle server notifications if needed
                    pass
            except json.JSONDecodeError:
                continue

    def _send_request(self, msg_id: str, method: str, params: dict):
        """Send a JSON-RPC request to the server's stdin."""
        if not self._process or not self._process.stdin:
            return
            
        self._response_queues[msg_id] = queue.Queue()
        request = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params
        }
        self._process.stdin.write(json.dumps(request) + "\n")
        self._process.stdin.flush()

    def _wait_for_response(self, msg_id: str, timeout: float) -> dict:
        """Wait for a response with a specific ID from the background reader."""
        try:
            q = self._response_queues.get(msg_id)
            if not q:
                raise RuntimeError(f"No response queue for ID {msg_id}")
            resp = q.get(timeout=timeout)
            if "error" in resp:
                raise RuntimeError(f"MCP Error: {resp['error']}")
            return resp.get("result", {})
        except queue.Empty:
            raise TimeoutError(f"MCP request {msg_id} timed out after {timeout}s")
        finally:
            if msg_id in self._response_queues:
                del self._response_queues[msg_id]

    def _get_mock_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "search_bibliography",
                "description": "Searches the Zotero library for authors, titles, or tags to find exact citations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The author name, year, or title to search for."}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search_scholar",
                "description": "Fallback Web Researcher: Searches Google Scholar or eLibrary for a citation if it is missing from Zotero.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Full text of the hallucinated or missing citation."}
                    },
                    "required": ["query"]
                }
            }
        ]

    def get_tools(self) -> List[Dict[str, Any]]:
        """Retrieve the JSON Schema tool definitions from the MCP server."""
        if not self.connected:
            self.connect()
        return self._tools
        
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any], run_id: Optional[str] = None, task: Optional[str] = None) -> Any:
        """Execute a tool on the remote MCP server or local researcher."""
        if not self.connected:
            self.connect()
            
        logger.info(f"Executing MCP Tool '{tool_name}' with args: {arguments}")
        
        result = None
        
        # 1. Try local Web Researcher first if it's the specific tool
        if tool_name == "search_scholar":
            from .researcher import WebResearcher
            researcher = WebResearcher()
            web_results = researcher.search(arguments.get("query", ""))
            result = {"status": "success", "source": "Web Researcher (OpenAlex)", "results": web_results}
            
        # 2. Otherwise, route to external MCP process if connected to one
        elif self._process and self._process.poll() is None:
            try:
                call_id = str(uuid.uuid4())
                self._send_request(call_id, "tools/call", {
                    "name": tool_name,
                    "arguments": arguments
                })
                result = self._wait_for_response(call_id, timeout=15)
            except Exception as e:
                logger.error(f"MCP Call failed for {tool_name}: {e}")
                
        # 3. Fallback to mock logic if not connected or call failed
        if result is None:
            result = self._execute_mock_logic(tool_name, arguments)

        if self._db and run_id and task:
            self._db.save_tool_call(run_id, task, tool_name, arguments, result)
            
        if self.on_tool_call and run_id:
            self.on_tool_call(run_id, {
                "type": "tool_call",
                "task": task,
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result
            })
            
        return result

    def _execute_mock_logic(self, tool_name: str, arguments: Dict[str, Any]) -> dict:
        result = {"status": "success", "results": []}
        if tool_name == "search_bibliography":
            query = arguments.get("query", "").lower()
            if "uspensky" in query or "успенский" in query:
                result = {
                    "status": "success",
                    "results": [{
                        "id": "Uspensky 1987",
                        "author": "Успенский Б. А.",
                        "year": 1987,
                        "title": "История русского литературного языка (Mock MCP Response)"
                    }]
                }
        return result

# Singleton instance for the pipeline
mcp_client = ZoteroMCPClient()
