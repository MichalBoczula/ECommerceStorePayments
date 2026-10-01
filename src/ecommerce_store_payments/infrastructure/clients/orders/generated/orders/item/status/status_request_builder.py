from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from kiota_abstractions.base_request_builder import BaseRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration
from kiota_abstractions.default_query_parameters import QueryParameters
from kiota_abstractions.get_path_parameters import get_path_parameters
from kiota_abstractions.method import Method
from kiota_abstractions.request_adapter import RequestAdapter
from kiota_abstractions.request_information import RequestInformation
from kiota_abstractions.request_option import RequestOption
from kiota_abstractions.serialization import Parsable, ParsableFactory
from typing import Any, Optional, TYPE_CHECKING, Union
from warnings import warn

if TYPE_CHECKING:
    from ....models.api_problem_details import ApiProblemDetails
    from ....models.conflict_problem_details import ConflictProblemDetails
    from ....models.not_found_problem_details import NotFoundProblemDetails
    from ....models.order_response_dto import OrderResponseDto
    from ....models.problem_details import ProblemDetails
    from ....models.update_order_status_request_dto import UpdateOrderStatusRequestDto

class StatusRequestBuilder(BaseRequestBuilder):
    """
    Builds and executes requests for operations under /orders/{orderId}/status
    """
    def __init__(self,request_adapter: RequestAdapter, path_parameters: Union[str, dict[str, Any]]) -> None:
        """
        Instantiates a new StatusRequestBuilder and sets the default values.
        param path_parameters: The raw url or the url-template parameters for the request.
        param request_adapter: The request adapter to use to execute the requests.
        Returns: None
        """
        super().__init__(request_adapter, "{+baseurl}/orders/{orderId}/status", path_parameters)

    async def patch(self,body: UpdateOrderStatusRequestDto, request_configuration: Optional[RequestConfiguration[QueryParameters]] = None) -> Optional[OrderResponseDto]:
        """
        Updates order status while enforcing allowed status transitions.
        param body: The request body
        param request_configuration: Configuration for the request such as headers, query parameters, and middleware options.
        Returns: Optional[OrderResponseDto]
        """
        if body is None:
            raise TypeError("body cannot be null.")
        request_info = self.to_patch_request_information(
            body, request_configuration
        )
        from ....models.api_problem_details import ApiProblemDetails
        from ....models.conflict_problem_details import ConflictProblemDetails
        from ....models.not_found_problem_details import NotFoundProblemDetails
        from ....models.problem_details import ProblemDetails

        error_mapping: dict[str, type[ParsableFactory]] = {
            "400": ApiProblemDetails,
            "404": NotFoundProblemDetails,
            "409": ConflictProblemDetails,
            "500": ProblemDetails,
        }
        if not self.request_adapter:
            raise Exception("Http core is null")
        from ....models.order_response_dto import OrderResponseDto

        return await self.request_adapter.send_async(request_info, OrderResponseDto, error_mapping)

    def to_patch_request_information(self,body: UpdateOrderStatusRequestDto, request_configuration: Optional[RequestConfiguration[QueryParameters]] = None) -> RequestInformation:
        """
        Updates order status while enforcing allowed status transitions.
        param body: The request body
        param request_configuration: Configuration for the request such as headers, query parameters, and middleware options.
        Returns: RequestInformation
        """
        if body is None:
            raise TypeError("body cannot be null.")
        request_info = RequestInformation(Method.PATCH, self.url_template, self.path_parameters)
        request_info.configure(request_configuration)
        request_info.headers.try_add("Accept", "application/json")
        request_info.set_content_from_parsable(self.request_adapter, "application/json", body)
        return request_info

    def with_url(self,raw_url: str) -> StatusRequestBuilder:
        """
        Returns a request builder with the provided arbitrary URL. Using this method means any other path or query parameters are ignored.
        param raw_url: The raw URL to use for the request builder.
        Returns: StatusRequestBuilder
        """
        if raw_url is None:
            raise TypeError("raw_url cannot be null.")
        return StatusRequestBuilder(self.request_adapter, raw_url)

    @dataclass
    class StatusRequestBuilderPatchRequestConfiguration(RequestConfiguration[QueryParameters]):
        """
        Configuration for the request such as headers, query parameters, and middleware options.
        """
        warn("This class is deprecated. Please use the generic RequestConfiguration class generated by the generator.", DeprecationWarning)
