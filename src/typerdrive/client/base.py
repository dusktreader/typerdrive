from typing import Any

import pydantic
from httpx import URL, Client, RequestError
from loguru import logger

from typerdrive.client.exceptions import ClientError


class TyperdriveClient(Client):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    def request_x[RM: pydantic.BaseModel](
        self,
        method: str,
        url: URL | str,
        *,
        param_obj: pydantic.BaseModel | None = None,
        body_obj: pydantic.BaseModel | None = None,
        expected_status: int | None = None,
        expect_response: bool = True,
        response_model: type[RM] | None = None,
        **request_kwargs: Any,
    ) -> RM | int | dict[str, Any]:
        logger.debug(f"Processing {method} request to {self.base_url.join(url)}")

        if param_obj is not None:
            logger.debug(f"Unpacking {param_obj=} to url params")

            ClientError.require_condition(
                "params" not in request_kwargs,
                "'params' not allowed when using param_obj",
            )
            with ClientError.handle_errors("Param data could not be deserialized for http request"):
                request_kwargs["params"] = param_obj.model_dump(mode="json")

        if body_obj is not None:
            logger.debug(f"Unpacking {body_obj=} to request body")

            ClientError.require_condition(
                all(k not in request_kwargs for k in ["data", "json", "content"]),
                "'data', 'json' and 'content' not allowed when using body_obj",
            )
            with ClientError.handle_errors("Request body data could not be deserialized for http request"):
                request_kwargs["content"] = body_obj.model_dump_json()
                request_kwargs["headers"] = {"Content-Type": "application/json"}

        with ClientError.handle_errors(
            "Communication with the API failed",
            handle_exc_class=RequestError,
        ):
            logger.debug("Issuing request")
            response = self.request(method, url, **request_kwargs)

        if expected_status is not None:
            logger.debug(f"Checking response for {expected_status=}")
            ClientError.require_condition(
                expected_status == response.status_code,
                "Got an unexpected status code: Expected {}, got {} -- {}".format(
                    expected_status, response.status_code, response.reason_phrase
                ),
                raise_kwargs=dict(details=response.text),
            )

        if not expect_response:
            logger.debug(f"Skipping response processing due to {expect_response=}")
            return response.status_code

        with ClientError.handle_errors("Failed to unpack JSON from response"):
            logger.debug("Parsing JSON from response")
            data: dict[str, Any] = response.json()

        if not response_model:
            logger.debug("Returning raw data due to no response model being supplied")
            return data

        with ClientError.handle_errors("Unexpected data in response"):
            logger.debug(f"Serializing response as {response_model.__name__}")
            return response_model(**data)

    def get_x[RM: pydantic.BaseModel](
        self,
        url: URL | str,
        *,
        param_obj: pydantic.BaseModel | None = None,
        body_obj: pydantic.BaseModel | None = None,
        expected_status: int | None = None,
        expect_response: bool = True,
        response_model: type[RM] | None = None,
        **request_kwargs: Any,
    ) -> RM | int | dict[str, Any]:
        return self.request_x(
            "GET",
            url,
            param_obj=param_obj,
            body_obj=body_obj,
            expected_status=expected_status,
            expect_response=expect_response,
            response_model=response_model,
            **request_kwargs,
        )

    def post_x[RM: pydantic.BaseModel](
        self,
        url: URL | str,
        *,
        param_obj: pydantic.BaseModel | None = None,
        body_obj: pydantic.BaseModel | None = None,
        expected_status: int | None = None,
        expect_response: bool = True,
        response_model: type[RM] | None = None,
        **request_kwargs: Any,
    ) -> RM | int | dict[str, Any]:
        return self.request_x(
            "POST",
            url,
            param_obj=param_obj,
            body_obj=body_obj,
            expected_status=expected_status,
            expect_response=expect_response,
            response_model=response_model,
            **request_kwargs,
        )

    def put_x[RM: pydantic.BaseModel](
        self,
        url: URL | str,
        *,
        param_obj: pydantic.BaseModel | None = None,
        body_obj: pydantic.BaseModel | None = None,
        expected_status: int | None = None,
        expect_response: bool = True,
        response_model: type[RM] | None = None,
        **request_kwargs: Any,
    ) -> RM | int | dict[str, Any]:
        return self.request_x(
            "PUT",
            url,
            param_obj=param_obj,
            body_obj=body_obj,
            expected_status=expected_status,
            expect_response=expect_response,
            response_model=response_model,
            **request_kwargs,
        )

    def patch_x[RM: pydantic.BaseModel](
        self,
        url: URL | str,
        *,
        param_obj: pydantic.BaseModel | None = None,
        body_obj: pydantic.BaseModel | None = None,
        expected_status: int | None = None,
        expect_response: bool = True,
        response_model: type[RM] | None = None,
        **request_kwargs: Any,
    ) -> RM | int | dict[str, Any]:
        return self.request_x(
            "PATCH",
            url,
            param_obj=param_obj,
            body_obj=body_obj,
            expected_status=expected_status,
            expect_response=expect_response,
            response_model=response_model,
            **request_kwargs,
        )

    def delete_x[RM: pydantic.BaseModel](
        self,
        url: URL | str,
        *,
        param_obj: pydantic.BaseModel | None = None,
        body_obj: pydantic.BaseModel | None = None,
        expected_status: int | None = None,
        expect_response: bool = True,
        response_model: type[RM] | None = None,
        **request_kwargs: Any,
    ) -> RM | int | dict[str, Any]:
        return self.request_x(
            "DELETE",
            url,
            param_obj=param_obj,
            body_obj=body_obj,
            expected_status=expected_status,
            expect_response=expect_response,
            response_model=response_model,
            **request_kwargs,
        )
