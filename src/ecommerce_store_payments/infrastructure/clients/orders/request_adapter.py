"""Require a success status with a body for the Orders GET operation."""

from httpx import Response
from kiota_abstractions.api_error import APIError
from kiota_http.httpx_request_adapter import HttpxRequestAdapter


class OrdersRequestAdapter(HttpxRequestAdapter):
    def _should_return_none(self, response: Response) -> bool:
        if response.status_code in {204, 304}:
            raise APIError("Orders returned an unexpected empty status.", response.status_code)
        return super()._should_return_none(response)
