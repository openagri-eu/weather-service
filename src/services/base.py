import httpx
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException

from src.core.exceptions import RefreshJWTTokenError


class MicroserviceClient:
    def __init__(
        self, base_url: str, service_name: str, app: FastAPI, timeout: float = 5.0
    ):
        self.base_url = base_url
        self.service_name = service_name
        self.app = app
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    def _get_auth_header(self) -> Dict[str, str]:
        # Get token from app.state
        token = self.app.state.access_token

        if not token:
            raise HTTPException(
                status_code=503, detail="Service JWT token not available"
            )

        return {"Authorization": f"Bearer {token}"}

    async def close(self):
        await self.client.aclose()

    async def request(
        self, method: str, endpoint: str, auth_required: bool = True, **kwargs
    ) -> Dict[str, Any]:

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Add auth headers if required
        headers = kwargs.get("headers", {})
        if auth_required:
            headers.update(self._get_auth_header())

        # Add common headers
        headers.update(
            {
                "Content-Type": "application/json",
                "X-Requesting-Service": self.service_name,
            }
        )

        kwargs["headers"] = headers

        try:
            response = await self.client.request(method, url, **kwargs)

            # Handle authentication errors
            if response.status_code == 401:
                # TODO: Remove unused code
                # await self.app.setup_authentication_tokens()
                raise RefreshJWTTokenError(self.service_name)

            # Raise exception for other error responses
            response.raise_for_status()

            # Return JSON response or empty dict for 204 No Content
            if response.status_code == 204:
                return {}
            return response.json()

        except httpx.HTTPStatusError as e:
            # Convert to FastAPI HTTPException with appropriate status code
            status_code = e.response.status_code
            try:
                detail = e.response.json()
            except:
                detail = str(e)

            raise HTTPException(
                status_code=status_code,
                detail=f"Service error ({self.service_name}): {detail}",
            )

        except httpx.RequestError as e:
            # Network or timeout errors
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable ({self.service_name}): {str(e)}",
            )

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ):
        return await self.request("GET", endpoint, params=params, **kwargs)

    async def post(
        self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs
    ):
        return await self.request("POST", endpoint, json=json, **kwargs)

    async def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs):
        return await self.request("PUT", endpoint, json=json, **kwargs)

    async def delete(self, endpoint: str, **kwargs):
        return await self.request("DELETE", endpoint, **kwargs)

    async def patch(
        self, endpoint: str, json: Optional[Dict[str, Any]] = None, **kwargs
    ):
        return await self.request("PATCH", endpoint, json=json, **kwargs)
