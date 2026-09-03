from mcp.server.mcpserver import MCPServer

if __package__:
    from .tools import register_file_tools
else:
    from tools import register_file_tools

#from services.customers import CustomerService
#from services.orders import OrderService

mcp = MCPServer("cowriter-app")

#customer_service = CustomerService()
#order_service = OrderService()

register_file_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
