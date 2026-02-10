"""
List all registered API routes
"""
from main import app

print("Registered API Routes:")
print("=" * 80)

for route in app.routes:
    if hasattr(route, 'methods'):
        methods = ', '.join(route.methods)
        print(f"{methods:10} {route.path:40} -> {route.name}")

print("=" * 80)
