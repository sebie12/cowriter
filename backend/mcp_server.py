import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

if __name__ == "__main__" and not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.tools import register_file_tools

#from services.customers import CustomerService
#from services.orders import OrderService

mcp = MCPServer("cowriter-app")

#customer_service = CustomerService()
#order_service = OrderService()

register_file_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
