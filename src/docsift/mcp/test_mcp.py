"""
MCP Server Test Script

This script demonstrates how to use the DocSift MCP server programmatically.
"""

import asyncio
import json
from docsift.mcp import (
    create_server,
    create_http_app,
    JsonRpcRequest,
    JsonRpcNotification,
)


async def test_stdio_mode():
    """Test stdio mode server."""
    print("=" * 60)
    print("Testing Stdio Mode")
    print("=" * 60)
    
    server = create_server()
    
    # 1. Initialize
    print("\n1. Sending initialize request...")
    request = JsonRpcRequest(
        id=1,
        method="initialize",
        params={
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    )
    response = await server.handle_request(request)
    print(f"   Response: {json.dumps(response.result, indent=2)}")
    
    # 2. Send initialized notification
    print("\n2. Sending initialized notification...")
    notification = JsonRpcNotification(
        method="notifications/initialized",
        params={}
    )
    await server.handle_notification(notification)
    print("   Done")
    
    # 3. List tools
    print("\n3. Listing tools...")
    request = JsonRpcRequest(
        id=2,
        method="tools/list",
        params={}
    )
    response = await server.handle_request(request)
    tools = response.result['tools']
    print(f"   Found {len(tools)} tools:")
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description'][:50]}...")
    
    # 4. Call query tool
    print("\n4. Calling query tool...")
    request = JsonRpcRequest(
        id=3,
        method="tools/call",
        params={
            "name": "query",
            "arguments": {"query": "machine learning", "limit": 3}
        }
    )
    response = await server.handle_request(request)
    content = response.result['content'][0]['text']
    result = json.loads(content)
    print(f"   Found {len(result['results'])} results")
    
    # 5. Call status tool
    print("\n5. Calling status tool...")
    request = JsonRpcRequest(
        id=4,
        method="tools/call",
        params={
            "name": "status",
            "arguments": {}
        }
    )
    response = await server.handle_request(request)
    content = response.result['content'][0]['text']
    result = json.loads(content)
    print(f"   Total documents: {result['total_documents']}")
    print(f"   Collections: {[c['name'] for c in result['collections']]}")
    
    print("\n✓ Stdio mode tests passed!")


def test_http_mode():
    """Test HTTP mode server."""
    print("\n" + "=" * 60)
    print("Testing HTTP Mode")
    print("=" * 60)
    
    app = create_http_app()
    print(f"\nFastAPI app created: {app.title} v{app.version}")
    
    print("\nRegistered routes:")
    for route in app.routes:
        if hasattr(route, 'methods'):
            methods = ','.join(route.methods)
            print(f"  {methods} {route.path}")
    
    print("\n✓ HTTP mode tests passed!")


async def main():
    """Run all tests."""
    await test_stdio_mode()
    test_http_mode()
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
