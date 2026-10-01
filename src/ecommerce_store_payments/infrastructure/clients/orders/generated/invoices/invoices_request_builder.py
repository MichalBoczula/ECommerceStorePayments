from __future__ import annotations
from collections.abc import Callable
from kiota_abstractions.base_request_builder import BaseRequestBuilder
from kiota_abstractions.get_path_parameters import get_path_parameters
from kiota_abstractions.request_adapter import RequestAdapter
from typing import Any, Optional, TYPE_CHECKING, Union
from uuid import UUID

if TYPE_CHECKING:
    from .by_order.by_order_request_builder import ByOrderRequestBuilder
    from .item.with_client_item_request_builder import WithClientItemRequestBuilder

class InvoicesRequestBuilder(BaseRequestBuilder):
    """
    Builds and executes requests for operations under /invoices
    """
    def __init__(self,request_adapter: RequestAdapter, path_parameters: Union[str, dict[str, Any]]) -> None:
        """
        Instantiates a new InvoicesRequestBuilder and sets the default values.
        param path_parameters: The raw url or the url-template parameters for the request.
        param request_adapter: The request adapter to use to execute the requests.
        Returns: None
        """
        super().__init__(request_adapter, "{+baseurl}/invoices", path_parameters)

    def by_client_id(self,client_id: UUID) -> WithClientItemRequestBuilder:
        """
        Gets an item from the ecommerce_store_payments.infrastructure.clients.orders.generated.invoices.item collection
        param client_id: Unique identifier of the item
        Returns: WithClientItemRequestBuilder
        """
        if client_id is None:
            raise TypeError("client_id cannot be null.")
        from .item.with_client_item_request_builder import WithClientItemRequestBuilder

        url_tpl_params = get_path_parameters(self.path_parameters)
        url_tpl_params["clientId"] = client_id
        return WithClientItemRequestBuilder(self.request_adapter, url_tpl_params)

    @property
    def by_order(self) -> ByOrderRequestBuilder:
        """
        The byOrder property
        """
        from .by_order.by_order_request_builder import ByOrderRequestBuilder

        return ByOrderRequestBuilder(self.request_adapter, self.path_parameters)
