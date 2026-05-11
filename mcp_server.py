"""MCP server for permission reviewer.

Exposes the permission reviewer as an MCP tool that Claude Code can call.

Usage:
    1. Add to Claude Code MCP servers in settings.json
    2. Claude Code can then call the permission_reviewer tools

Example settings.json:
{
  "mcpServers": {
    "permission-reviewer": {
      "command": "python",
      "args": ["-m", "agents.permission_reviewer.mcp"]
    }
  }
}
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import json
from agents.permission_reviewer.agent import PermissionReviewAgent
from agents.permission_reviewer.context import get_session_context, get_recent_changes_analyzer

# MCP protocol helpers
STDIN_READY = sys.platform == "win32"

def send_response(response: dict):
    """Send JSON response to stdout."""
    print(json.dumps(response), flush=True)

def read_request() -> dict | None:
    """Read JSON request from stdin."""
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return json.loads(line)
    except json.JSONDecodeError:
        return None

async def handle_request(request: dict) -> dict:
    """Handle an MCP request."""
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "permission-reviewer",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "review_permission",
                        "description": "Review a permission request using LLM with project context. Returns ALLOW, DENY, or REVIEW decision.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "permission": {
                                    "type": "string",
                                    "description": "Permission type (Bash, Write, Read, Agent, etc.)",
                                    "enum": ["Bash", "Write", "Read", "Agent", "WebFetch", "WebSearch"]
                                },
                                "tool_name": {"type": "string", "description": "The tool being invoked"},
                                "command": {"type": "string", "description": "For Bash: the command to execute"},
                                "target": {"type": "string", "description": "For file operations: the target path"},
                                "description": {"type": "string", "description": "Human-readable description of the operation"}
                            },
                            "required": ["permission"]
                        }
                    },
                    {
                        "name": "set_session_context",
                        "description": "Set the current session context so the reviewer understands what the main agent is working on.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task": {"type": "string", "description": "Current task description"},
                                "target_file": {"type": "string", "description": "Target file being worked on"},
                                "goals": {"type": "array", "items": {"type": "string"}, "description": "List of goals"},
                                "constraints": {"type": "array", "items": {"type": "string"}, "description": "List of constraints"}
                            },
                            "required": ["task"]
                        }
                    },
                    {
                        "name": "add_context_action",
                        "description": "Record an action the main agent has taken.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "description": "Action description"},
                                "details": {"type": "string", "description": "Additional details"}
                            },
                            "required": ["action"]
                        }
                    },
                    {
                        "name": "get_session_context",
                        "description": "Get the current session context summary.",
                        "inputSchema": {"type": "object", "properties": {}}
                    }
                ]
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "review_permission":
                agent = PermissionReviewAgent()
                result = await agent.review(
                    permission=arguments.get("permission", ""),
                    tool_name=arguments.get("tool_name"),
                    command=arguments.get("command"),
                    target=arguments.get("target"),
                    description=arguments.get("description"),
                )

                # Format as MCP tool result
                content = f"Decision: {result['decision'].upper()}\n"
                content += f"Reason: {result['reason']}\n"
                if result.get("suggestion"):
                    content += f"Suggestion: {result['suggestion']}"

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": content}]
                    }
                }

            elif tool_name == "set_session_context":
                ctx = get_session_context()
                ctx.update_task(
                    arguments.get("task", ""),
                    arguments.get("target_file")
                )
                if arguments.get("goals"):
                    ctx.set_goals(arguments["goals"])
                for constraint in arguments.get("constraints", []):
                    ctx.add_constraint(constraint)

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": "Context updated successfully"}]
                    }
                }

            elif tool_name == "add_context_action":
                ctx = get_session_context()
                ctx.add_action(
                    arguments.get("action", ""),
                    arguments.get("details")
                )

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": "Action recorded"}]
                    }
                }

            elif tool_name == "get_session_context":
                ctx = get_session_context()
                summary = ctx.get_context_summary()

                # Also get recent changes
                analyzer = get_recent_changes_analyzer()
                changes = analyzer.get_recent_file_changes(minutes=60)

                content = f"Current Context:\n{summary}\n\n"
                if changes:
                    content += "Recent Changes:\n"
                    for c in changes[:10]:
                        content += f"- [{c['type']}] {c['path']}\n"

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": content}]
                    }
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)}
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }


async def main():
    """Main MCP server loop."""
    # Send ready signal
    if STDIN_READY:
        print("MCP server starting...", flush=True)

    while True:
        request = read_request()
        if request is None:
            break

        response = await handle_request(request)
        if response:
            send_response(response)


if __name__ == "__main__":
    asyncio.run(main())
