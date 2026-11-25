"""Local test server using an in-memory database (NOT for production). Used only for browser testing."""
import sys
sys.path.insert(0, "backend")
from app import create_app
create_app(testing=True).run(port=5055)
