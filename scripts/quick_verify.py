import asyncio
import aiohttp
import sys
import time
from typing import Dict, List

class QuickVerifier:
    def __init__(self):
        self.services = {
            "Search Service": {"port": 7001, "path": "/health/", "swagger": "/docs"},
            "Recommendation Service": {"port": 7002, "path": "/health/", "swagger": "/docs"},
            "Analytics Service": {"port": 7004, "path": "/health/", "swagger": "/docs"},
            "Shopping Assistant": {"port": 7005, "path": "/health/", "swagger": "/docs"}
        }
        self.infrastructure = {
            "PostgreSQL": {"port": 7010, "check": self._check_postgres},
            "Redis": {"port": 7011, "check": self._check_redis},
            "Elasticsearch": {"port": 9200, "path": "/_cluster/health"},
            "Weaviate": {"port": 8065, "path": "/v1/meta"}
        }
        self.summary = []

    def _print_status(self, name: str, status: bool, message: str):
        if status:
            print(f"✅ {name}: {message}")
        else:
            print(f"❌ {name}: {message}")
        self.summary.append((name, status, message))

    async def _http_get_check(self, name: str, port: int, path: str = "/") -> bool:
        url = f"http://localhost:{port}{path}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if 200 <= response.status < 400:
                        return True
                    else:
                        return False
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False

    async def _check_postgres(self) -> bool:
        # PostgreSQL check via `pg_isready` (requires psql client or docker exec)
        # For quick_verify, we'll just check if the port is open and assume Docker Compose healthcheck is robust.
        return await self._is_port_open(self.infrastructure["PostgreSQL"]["port"])

    async def _check_redis(self) -> bool:
        # Redis check (requires redis-cli or docker exec)
        # For quick_verify, we'll just check if the port is open.
        return await self._is_port_open(self.infrastructure["Redis"]["port"])

    async def _is_port_open(self, port: int) -> bool:
        try:
            reader, writer = await asyncio.open_connection('localhost', port)
            writer.close()
            await writer.wait_closed()
            return True
        except (ConnectionRefusedError, asyncio.TimeoutError):
            return False

    async def run_checks(self):
        print("\n--- Infrastructure Checks ---")
        for name, config in self.infrastructure.items():
            if "check" in config:
                status = await config["check"]()
                self._print_status(name, status, "Running" if status else "Not reachable or unhealthy")
            else:
                status = await self._http_get_check(name, config["port"], config["path"])
                self._print_status(name, status, "Responding" if status else "Not responding or unhealthy")
        
        print("\n--- Backend Service Health Checks ---")
        for name, config in self.services.items():
            status = await self._http_get_check(name, config["port"], config["path"])
            self._print_status(name, status, "Healthy" if status else "Unhealthy")

        print("\n--- Summary ---")
        all_passed = True
        for name, status, message in self.summary:
            if status:
                print(f"✅ {name}")
            else:
                print(f"❌ {name}: {message}")
                all_passed = False
        
        print("\n--- Access URLs ---")
        for name, config in self.services.items():
            if name == "Search Service": print(f"  - {name} Swagger UI: http://localhost:{config["port"]}{config["swagger"]}")
            if name == "Recommendation Service": print(f"  - {name} Swagger UI: http://localhost:{config["port"]}{config["swagger"]}")
            if name == "Analytics Service": print(f"  - {name} Swagger UI: http://localhost:{config["port"]}{config["swagger"]}")
            if name == "Shopping Assistant": print(f"  - {name} Swagger UI: http://localhost:{config["port"]}{config["swagger"]}")
        print(f"  - Elasticsearch: http://localhost:{self.infrastructure['Elasticsearch']['port']}{self.infrastructure['Elasticsearch']['path']}")
        print(f"  - Weaviate: http://localhost:{self.infrastructure['Weaviate']['port']}{self.infrastructure['Weaviate']['path']}")

        if all_passed:
            print("\n🎉 All essential services are running and healthy!")
            sys.exit(0)
        else:
            print("\n⚠️  Some services are not healthy. Please check `docker-compose logs` for details.")
            sys.exit(1)

async def main():
    verifier = QuickVerifier()
    await verifier.run_checks()

if __name__ == "__main__":
    asyncio.run(main())
