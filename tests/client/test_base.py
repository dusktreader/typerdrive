import json

import httpx
import pydantic
import pytest
import respx
from typerdrive.client.base import TyperdriveClient
from typerdrive.client.exceptions import ClientError


class QueryParams(pydantic.BaseModel):
    anger: bool
    fear: bool
    aggression: bool


class RequestBody(pydantic.BaseModel):
    anger: bool
    fear: bool
    aggression: bool


class ResponseModel(pydantic.BaseModel):
    speed: str
    difficulty: str
    attractiveness: str


class TestRequestX:
    def test_request_x__basic(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200, json=dict(speed="quicker", difficulty="easier", attractiveness="seductive")
            )
        )

        response = client.request_x("GET", "the-dark-side")

        assert mock_route.called
        assert isinstance(response, dict)
        assert response == dict(speed="quicker", difficulty="easier", attractiveness="seductive")

    def test_request_x__with_param_obj(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(speed="quicker", difficulty="easier", attractiveness="seductive"),
            )
        )
        client.request_x("GET", "the-dark-side", param_obj=QueryParams(anger=True, fear=True, aggression=True))

        assert mock_route.called
        assert dict(mock_route.calls.last.request.url.params) == dict(anger="true", fear="true", aggression="true")

    def test_request_x__raises_exception_when_params_provided_with_param_obj(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock()
        with pytest.raises(ClientError, match="'params' not allowed"):
            client.request_x(
                "GET",
                "the-dark-side",
                params=dict(anger=True),
                param_obj=QueryParams(anger=True, fear=True, aggression=True),
            )

        assert not mock_route.called

    def test_request_x__raises_exception_for_invalid_param_obj(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock()
        with pytest.raises(ClientError, match="Param data could not be deserialized"):
            client.request_x("GET", "the-dark-side", param_obj="not a pydantic model instance")  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]

        assert not mock_route.called

    def test_request_x__with_body_obj(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.post("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(speed="quicker", difficulty="easier", attractiveness="seductive"),
            )
        )
        client.request_x("POST", "the-dark-side", body_obj=RequestBody(anger=True, fear=True, aggression=True))

        assert mock_route.called
        assert mock_route.calls.last.request.headers["Content-Type"] == "application/json"
        assert json.loads(mock_route.calls.last.request.content.decode("utf-8")) == dict(
            anger=True,
            fear=True,
            aggression=True,
        )

    def test_request_x__raises_exception_when_body_provided_with_body_obj(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.post("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(speed="quicker", difficulty="easier", attractiveness="seductive"),
            )
        )
        with pytest.raises(ClientError, match="'data', 'json' and 'content' not allowed"):
            client.request_x(
                "POST",
                "the-dark-side",
                json=dict(anger=True),
                body_obj=RequestBody(anger=True, fear=True, aggression=True),
            )

        assert not mock_route.called

    def test_request_x__raises_exception_for_invalid_body_model(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.post("https://the.force.io/the-dark-side").mock()
        with pytest.raises(ClientError, match="Request body data could not be deserialized"):
            client.request_x(
                "POST",
                "the-dark-side",
                body_obj="not a pydantic model instance",  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
            )

        assert not mock_route.called

    def test_request_x__raises_exception_when_httpx_request_fails(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        respx_mock.get("https://the.force.io/the-dark-side").mock(side_effect=httpx.RequestError("Boom!"))
        with pytest.raises(ClientError, match="Communication with the API failed"):
            client.request_x("GET", "the-dark-side")

    def test_request_x__raises_exception_when_status_code_does_not_match_expected(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(status_code=202)
        )

        with pytest.raises(ClientError, match="Got an unexpected status code: Expected 200, got 202"):
            client.request_x("GET", "the-dark-side", expected_status=200)

        assert mock_route.called

    def test_request_x__just_returns_status_code_if_not_expect_response(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(status_code=204)
        )

        response = client.request_x("GET", "the-dark-side", expect_response=False)

        assert mock_route.called
        assert response == 204

    def test_request_x__raises_exception_if_response_does_not_unpack(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(status_code=200, content="NOT SERIALIZABLE"),
        )

        with pytest.raises(ClientError, match="Failed to unpack JSON"):
            client.request_x("GET", "the-dark-side")

        assert mock_route.called

    def test_request_x__returns_dict_if_response_model_is_not_provided(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200, json=dict(speed="quicker", difficulty="easier", attractiveness="seductive")
            )
        )

        response = client.request_x("GET", "the-dark-side")

        assert mock_route.called
        assert isinstance(response, dict)
        assert response == dict(speed="quicker", difficulty="easier", attractiveness="seductive")

    def test_request_x__deserializes_to_response_model_if_provided(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200, json=dict(speed="quicker", difficulty="easier", attractiveness="seductive")
            )
        )

        response = client.request_x("GET", "the-dark-side", response_model=ResponseModel)

        assert mock_route.called
        assert isinstance(response, ResponseModel)
        assert response == ResponseModel(speed="quicker", difficulty="easier", attractiveness="seductive")

    def test_request_x__raises_exception_when_body_cannot_be_deserialized_to_response_model(
        self, respx_mock: respx.MockRouter
    ):
        class OtherModel(pydantic.BaseModel):
            planet: str

        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200, json=dict(speed="quicker", difficulty="easier", attractiveness="seductive")
            )
        )

        with pytest.raises(ClientError, match="Unexpected data in response"):
            client.request_x("GET", "the-dark-side", response_model=OtherModel)

        assert mock_route.called


class TestGetX:
    def test_get_x(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.get("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200, json=dict(speed="quicker", difficulty="easier", attractiveness="seductive")
            )
        )

        response = client.get_x(
            "the-dark-side",
            param_obj=QueryParams(anger=True, fear=True, aggression=True),
            response_model=ResponseModel,
        )

        assert mock_route.called
        assert isinstance(response, ResponseModel)
        assert response == ResponseModel(speed="quicker", difficulty="easier", attractiveness="seductive")


class TestPostX:
    def test_post_x(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.post("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200, json=dict(speed="quicker", difficulty="easier", attractiveness="seductive")
            )
        )

        response = client.post_x(
            "the-dark-side",
            body_obj=RequestBody(anger=True, fear=True, aggression=True),
            response_model=ResponseModel,
        )

        assert mock_route.called
        assert isinstance(response, ResponseModel)
        assert response == ResponseModel(speed="quicker", difficulty="easier", attractiveness="seductive")


class TestPutX:
    def test_put_x(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.put("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200, json=dict(speed="quicker", difficulty="easier", attractiveness="seductive")
            )
        )

        response = client.put_x(
            "the-dark-side",
            body_obj=RequestBody(anger=True, fear=True, aggression=True),
            response_model=ResponseModel,
        )

        assert mock_route.called
        assert isinstance(response, ResponseModel)
        assert response == ResponseModel(speed="quicker", difficulty="easier", attractiveness="seductive")


class TestPatchX:
    def test_put_x(self, respx_mock: respx.MockRouter):
        client = TyperdriveClient(base_url="https://the.force.io")

        mock_route = respx_mock.patch("https://the.force.io/the-dark-side").mock(
            return_value=httpx.Response(
                status_code=200, json=dict(speed="quicker", difficulty="easier", attractiveness="seductive")
            )
        )

        response = client.patch_x(
            "the-dark-side",
            body_obj=RequestBody(anger=True, fear=True, aggression=True),
            response_model=ResponseModel,
        )

        assert mock_route.called
        assert isinstance(response, ResponseModel)
        assert response == ResponseModel(speed="quicker", difficulty="easier", attractiveness="seductive")
