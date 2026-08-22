import pytest

from app import create_app


@pytest.fixture
def app():
    app = create_app(testing=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_factory(app):
    from tests.helpers import create_user

    return lambda **kw: create_user(app, **kw)


@pytest.fixture
def channel_factory(app):
    from tests.helpers import create_channel

    return lambda **kw: create_channel(app, **kw)