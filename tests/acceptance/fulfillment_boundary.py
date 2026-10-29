"""Explicit controlled Orders/Invoice HTTP state; all traffic uses the real Kiota adapters."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from httpx import ReadTimeout, Request, Response

if TYPE_CHECKING:
    from tests.acceptance.conftest import OrdersBoundary

DATA_VERSION = UUID("33333333-3333-4333-8333-333333333333")
OLDER_VERSION = UUID("44444444-4444-4444-8444-444444444444")


class FulfillmentBoundary:
    def __init__(self, orders: OrdersBoundary, mode: str) -> None:
        self.orders, self.mode = orders, mode
        self.invoice: dict[str, Any] | None = None
        self.trace: list[dict[str, Any]] = []
        self.logical_paid: int = 0
        self.logical_invoices: int = 0
        self.local_fault: str | None = None
        self.version = DATA_VERSION
        if mode in {"already_paid", "existing_invoice", "lookup_wrong_order", "lookup_zero_version"}:
            orders.status = "Paid"
        if mode in {"existing_invoice", "lookup_wrong_order", "lookup_zero_version"}:
            self.version = OLDER_VERSION
            self.invoice = self.new_invoice()

    def new_invoice(self) -> dict[str, Any]:
        invoice_id = self.orders.invoice_id or uuid4()
        self.orders.invoice_id = invoice_id
        return {
            "id": str(invoice_id),
            "orderId": str(self.orders.order_id),
            "clietDataVersionId": str(self.version),
            "storageUrl": f"file:///controlled/{invoice_id}.pdf",
            "createdAt": datetime.now(UTC).isoformat(),
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "orderId": str(self.orders.order_id),
            "clientId": str(self.orders.client_id),
            "status": self.orders.status,
            "invoice": deepcopy(self.invoice),
            "logicalPaidWrites": self.logical_paid,
            "logicalInvoices": self.logical_invoices,
        }

    def order_response(self) -> Response:
        amount = "13.00" if self.mode == "wrong_amount" else format(self.orders.amount, "f")
        status = "Cancelled" if self.mode == "cancelled" else self.orders.status
        return Response(
            200,
            content=(
                json.dumps(
                    {
                        "id": str(self.orders.order_id),
                        "clientId": str(self.orders.client_id),
                        "status": status,
                        "totalCurrency": self.orders.currency,
                    }
                )[:-1]
                + ',"totalAmount":'
                + amount
                + ',"lines":[{"lineTotalAmount":'
                + amount
                + ',"productVersion":{"priceCurrency":"PLN"}}]}'
            ).encode(),
            headers={"content-type": "application/json"},
        )

    def handle(self, request: Request) -> Response:
        path, method = request.url.path, request.method
        order_path = f"/orders/{self.orders.order_id}"
        lookup_path = f"/invoices/by-order/{self.orders.order_id}"
        create_path = f"/invoices/{self.orders.client_id}/{self.orders.order_id}"
        assert (method, path) in {
            ("GET", order_path),
            ("PATCH", order_path + "/status"),
            ("GET", lookup_path),
            ("POST", create_path),
        }
        body = request.read()
        assert json.loads(body) == {"status": "Paid"} if method == "PATCH" else body == b""
        label = (
            "paid"
            if method == "PATCH"
            else "create"
            if method == "POST"
            else "invoice"
            if path == lookup_path
            else "order"
        )
        result: Response
        mode = self.mode
        if label == "order":
            self.orders.calls += 1
            if mode == "order_500":
                result = Response(500, json={"private": "controlled upstream error"})
            elif mode == "order_401":
                result = Response(401, json={"private": "controlled upstream error"})
            else:
                result = self.order_response()
        elif label == "paid":
            self.orders.paid_writes += 1
            if mode in {"patch_409", "patch_unconfirmed"}:
                result = Response(409) if mode == "patch_409" else self.order_response()
            else:
                if self.orders.status != "Paid":
                    self.logical_paid += 1
                self.orders.status = "Paid"
                if mode == "paid_ack_lost":
                    self.mode = "ok"
                    self.trace.append({"method": method, "path": path, "result": "ReadTimeout"})
                    raise ReadTimeout("controlled lost Paid acknowledgement", request=request)
                result = Response(409) if mode == "paid_409_committed" else self.order_response()
        elif label == "invoice":
            if mode == "lookup_500":
                result = Response(500, json={"private": "controlled invoice lookup"})
            elif mode == "lookup_403":
                result = Response(403, json={"private": "controlled invoice lookup"})
            elif self.invoice is None:
                result = Response(404)
            else:
                payload = deepcopy(self.invoice)
                if mode == "lookup_wrong_order":
                    payload["orderId"] = "88888888-8888-4888-8888-888888888888"
                if mode == "lookup_zero_version":
                    payload["clietDataVersionId"] = str(UUID(int=0))
                result = Response(200, json=payload)
        else:
            self.orders.invoice_creates += 1
            if mode in {"pdf_failure", "invoice_409", "invoice_404", "create_403"}:
                status = {"pdf_failure": 500, "invoice_409": 409, "invoice_404": 404, "create_403": 403}[mode]
                if mode == "pdf_failure":
                    self.mode = "ok"
                result = Response(status, json={"private": "controlled invoice creation failure"})
            else:
                if self.invoice is None:
                    self.invoice = self.new_invoice()
                    self.logical_invoices += 1
                if mode == "invoice_ack_lost":
                    self.mode = "ok"
                    self.trace.append({"method": method, "path": path, "result": "ReadTimeout"})
                    raise ReadTimeout("controlled lost invoice acknowledgement", request=request)
                payload = deepcopy(self.invoice)
                if mode == "create_invalid":
                    payload["storageUrl"] = ""
                result = Response(200, json=payload)
        self.trace.append({"method": method, "path": path, "result": result.status_code})
        return result
