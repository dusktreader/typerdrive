"""
Provide a specialized HTTP client for making requests to APIs.
"""

from typing import Any

import pydantic
from httpx import URL, Client, RequestError
from loguru import logger

from typerdrive.client.exceptions import ClientError


class TyperdriveClient(Client):
    """
    Extend the `http.Client` with `*_x()` methods that provide useful features for processing requests.
    """

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
        """
        Make a request against an API.

        Provides functionality to take url params and request body from instances of `pydantic` models.
        Also, provides checks for the status code returned from the API.
        Will deserialize the response into a `pydantic` model if one is provided.

        Note that all the arguments of `httpx.Client` are also supported.

        Parameters:
            method:           The HTTP method to use in the request
            url:              The url to use for the request. Will be appended to `base_url` if one has been set.
            param_obj:        An optional `pydantic` model to use for url params. This will be serialized to JSON and
                              passed as the request URL parameters.
                              If set, and params are passed through another mechanism as well, an exception will be
                              raised.
            body_obj:         An optional `pydantic` model to use for request body. This will be serialized to JSON and
                              passed as the request body.
                              If set, and the body is passed through another mechanism as well, an exception will be
                              raised.
            expected_status:  If provided, check the response code from the API. If the code doesn't match, raise an
                              exception.
            expect_response:  If set, expect the response to have a JSON body that needs to be deserialized. If not set,
                              just return the status code.
            response_model:   If provided, deserialize the response into an instance of this model. If not provided,
                              the return value will just be a dictionary containing the response data.
        """
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
        """
        Make a GET request against an API using the `request_x()` method.
        """
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
        """
        Make a POST request against an API using the `request_x()` method.
        """
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
        """
        Make a PUT request against an API using the `request_x()` method.
        """
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
        """
        Make a PATCH request against an API using the `request_x()` method.
        """
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
        """
        Make a DELETE request against an API using the `request_x()` method.
        """
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
