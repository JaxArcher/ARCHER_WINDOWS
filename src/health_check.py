"""
ARCHER Health Check Endpoint
Provides system status monitoring for Docker health checks
"""

from flask import Flask, jsonify
import torch
import time
import psutil
import os
from pathlib import Path

app = Flask(__name__)


@app.route("/health")
def health_check():
    """Comprehensive health check endpoint."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {
                "gpu": {
                    "available": torch.cuda.is_available(),
                    "count": torch.cuda.device_count()
                    if torch.cuda.is_available()
                    else 0,
                    "memory": {
                        "used": torch.cuda.memory_allocated(0) // 1024**2
                        if torch.cuda.is_available()
                        else 0,
                        "total": torch.cuda.get_device_properties(0).total_memory
                        // 1024**2
                        if torch.cuda.is_available()
                        else 0,
                    }
                    if torch.cuda.is_available()
                    else None,
                },
                "cpu": {
                    "usage": psutil.cpu_percent(interval=1),
                    "memory": {
                        "used": psutil.virtual_memory().used // 1024**2,
                        "total": psutil.virtual_memory().total // 1024**2,
                        "percent": psutil.virtual_memory().percent,
                    },
                },
                "disk": {
                    "used": psutil.disk_usage("/").used // 1024**2,
                    "total": psutil.disk_usage("/").total // 1024**2,
                    "percent": psutil.disk_usage("/").percent,
                },
            },
            "services": {
                "indextts": check_service("indextts", 7861),
                "lm_studio": check_service("lm-studio", 1234),
            },
        }

        # Determine overall status
        if not health_status["components"]["gpu"]["available"]:
            health_status["status"] = "degraded"
        elif health_status["components"]["cpu"]["memory"]["percent"] > 90:
            health_status["status"] = "warning"
        elif any(
            not service["available"] for service in health_status["services"].values()
        ):
            health_status["status"] = "degraded"

        return jsonify(health_status), 200

    except Exception as e:
        return jsonify(
            {"status": "unhealthy", "error": str(e), "timestamp": time.time()}
        ), 500


def check_service(name, port):
    """Check if a service is available."""
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return {"available": result == 0, "port": port}
    except:
        return {"available": False, "port": port}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
