"""
SchemaSentry - Main Entry Point
Run with: python main.py
"""

import uvicorn
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import config


def main():
    """Start the SchemaSentry server."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🛡️  SchemaSentry - Smart API Contract Guardian              ║
║                                                               ║
║   Detect breaking API changes before clients do.              ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Check for API key
    if not config.GROQ_API_KEY:
        print("⚠️  Warning: GROQ_API_KEY not set!")
        print("   Set it in .env file or as environment variable.")
        print("   Get your key at: https://console.groq.com/keys")
        print()
    
    print(f"🚀 Starting server at http://{config.HOST}:{config.PORT}")
    print(f"📖 API docs at http://{config.HOST}:{config.PORT}/docs")
    print(f"🎨 Dashboard at http://{config.HOST}:{config.PORT}/")
    print()
    
    uvicorn.run(
        "api.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
    )


if __name__ == "__main__":
    main()
