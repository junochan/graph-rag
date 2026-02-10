"""
Flask application factory and main entry point.
"""

import logging
from flask import Flask
from flask_restx import Api

from src.config import get_settings


def create_app() -> Flask:
    """Create and configure Flask application."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    app = Flask(__name__)
    app.config["DEBUG"] = settings.debug

    # Initialize Flask-RESTX API with Swagger
    api = Api(
        app,
        version="1.0.0",
        title="Graph RAG API",
        description="Graph-based Retrieval Augmented Generation API with NebulaGraph and configurable vector stores",
        doc="/docs",  # Swagger UI endpoint
        prefix="/api",
    )

    # Register namespaces
    from src.api.build import api as build_ns
    from src.api.retrieve import api as retrieve_ns

    api.add_namespace(build_ns, path="/build")
    api.add_namespace(retrieve_ns, path="/retrieve")

    # Health check endpoint
    @app.route("/health")
    def health_check():
        return {"status": "healthy", "app": settings.app_name}

    # Info endpoint (not root to avoid conflict with Flask-RESTX)
    @app.route("/info")
    def info():
        return {
            "app": settings.app_name,
            "version": "1.0.0",
            "docs": "/docs",
            "api": "/api",
        }

    return app


def run_server():
    """Run the development server."""
    settings = get_settings()
    app = create_app()
    app.run(
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
    )


if __name__ == "__main__":
    run_server()
