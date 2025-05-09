from datetime import datetime
from typing import cast

from pydantic import BaseModel
from typerdrive import TyperdriveClient


def demo_1__typerdrive_client__using_a_query_param_model():
    """
    This function demonstrates how the `_x()` methods of the `TyperdriveClient`
    can use a pydantic model to provide query parameters to the request. In this
    case, the `get_x()` method takes a `param_obj` keyword argument that provides
    all the query parameters that are used in the request. You may not use the
    `params` keyword argument used by normal `httx.Client` instances if you use
    the `param_obj` parameter.
    """

    class QueryParams(BaseModel):
        search: str

    class People(BaseModel, extra="ignore"):
        name: str
        birth_year: str
        gender: str

    class ResponseModel(BaseModel, extra="ignore"):
        results: list[People]

    client = TyperdriveClient(base_url="https://swapi.py4e.com/api/")
    param_obj = QueryParams(search="skywalker")
    response = cast(
        ResponseModel,
        client.get_x("people/", param_obj=param_obj, response_model=ResponseModel),
    )
    print("People ->", ", ".join(r.name for r in response.results))


def demo_2__typerdrive_client__using_a_request_body_model():
    """
    This function demonstrates how the `_x()` methods of the `TyperdriveClient`
    can use a pydantic model to provide a request body. In this case, the
    `post_x()` method takes a `body_obj` keyword argument that provides the
    complete body for the request. You may not use other keyword arguments such
    as `data`, `json`, or `content` if you use the `body_obj` parameter.
    """

    class PeopleData(BaseModel):
        birth_year: str
        gender: str
        species: str

    class Body(BaseModel):
        name: str
        data: PeopleData

    class ResponseModel(BaseModel, extra="ignore"):
        id: str
        name: str
        createdAt: datetime
        data: PeopleData

    client = TyperdriveClient(base_url="https://api.restful-api.dev/")
    body_obj = Body(name="Mara Jade Skywalker", data=PeopleData(birth_year="17 BBY", gender="Female", species="Human"))
    response = cast(
        ResponseModel,
        client.post_x("objects", body_obj=body_obj, response_model=ResponseModel),
    )
    print("New Person ->", response)


def demo_3__typerdrive_client__expecting_specific_status():
    """
    This function demonstrates how the `_x()` methods of the `TyperdriveClient`
    can specify the exact status code that they want to receive. If that status
    code is not returned, they will raise a `ClientError`.
    """

    client = TyperdriveClient(base_url="https://swapi.py4e.com/api/")
    client.get_x("people/1/", expected_status=203)


def demo_4__typerdrive_client__with_no_expected_response():
    """
    This function demonstrates how the `_x()` methods of the `TyperdriveClient`
    can disregard the response and only return the status code. This is useful
    for any endpoints that do may not return a body, and you are only concerned
    that the request was successful.
    """
    client = TyperdriveClient(base_url="https://swapi.py4e.com/api/")
    response = client.get_x("people/1/", expect_response=False)
    print("Status Code ->", response)


def demo_5__typerdrive_client__with_no_response_model():
    """
    This function demonstrates how the `_x()` methods of the `TyperdriveClient`
    can return a plain dictionary from the JSON body of the response if no
    `response_model` is provided.
    """
    client = TyperdriveClient(base_url="https://swapi.py4e.com/api/")
    response = client.get_x("people/1/")
    print("Raw Data ->", response)
