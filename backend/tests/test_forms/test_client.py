#!/usr/bin/env python3
"""
This contains test for artisan profile form
"""
from flask.testing import FlaskClient
from flask_sqlalchemy import SQLAlchemy
import pytest
from flask import Flask
from extensions import db, jwt, redis_client
# The unused models are needed for mapping
from models.user import User
from models.artisan import Artisan
from models.client import Client
from models.booking import Booking
from forms.client import ClientProfileForm
from routes.auth import users_Bp
from routes.client import clients_Bp
from datetime import datetime, timezone


@pytest.fixture(scope="module")
def app() -> Flask:
    """ Create a new Flask instance for test """
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "test_secret_key"
    # commented cause my validate_on_submit method depends on CSRF failure
    # app.config["WTF_CSRF_ENABLED"] = False
    app.config["JWT_VERIFY_SUB"] = False

    # Bind SQLAlchemy to the Flask app
    db.init_app(app)

    # Initialize JWT
    jwt.init_app(app)
    # Initialize redis
    redis_client.init_app(app)

    # Register blueprints
    app.register_blueprint(users_Bp)
    app.register_blueprint(clients_Bp)

    return app


@pytest.fixture(scope="module")
def database(app: Flask):
    """ work wiht database """
    with app.app_context():
        # Create tables
        db.create_all()
        # Provide the database object to the test
        yield db
        # Clean up tables after tests
        db.drop_all()


@pytest.fixture(scope="module")
def client(app: Flask):
    return app.test_client()


@pytest.fixture(scope="module")
def user_and_token(client: FlaskClient, database: SQLAlchemy):
    # Register the user
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'securepassword',
        'confirm_password': 'securepassword',
        'phone_number': '+1234567890',
        'location': 'Test Location',
        'role': 'Client',
    })
    assert response.status_code == 201

    # Log in the user
    login_response = client.post('/login', data={
        'email': 'testuser@example.com',
        'password': 'securepassword'
    })
    assert login_response.status_code == 200
    user = User.query.filter_by(username="testuser").first()
    token = login_response.json['access_token']
    return user, token


def test_client_profile_form_valid(
        client: FlaskClient, user_and_token: tuple):
    """ Test client profile form with valid fields """
    user, token = user_and_token
    form = ClientProfileForm(
        username="testuser",
        email="test@example.com",
        phone_number="+1234567890",
        location="Somewhere",
        specialization="Engineering",
        skills="coding and testing",
        picture="default.jpeg",
        submit="True",
    )
    response = client.post('/client', data=form.data, headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 200
    assert response.json == user.client.to_dict()


def test_client_profile_form_invalid_email(
        client: FlaskClient, user_and_token: tuple):
    """ Test client profile form with invalid email """
    _, token = user_and_token
    form = ClientProfileForm(
        username="testuser",
        email="Invalid",
        phone_number="+1234567890",
        location="Somewhere",
        specialization="Engineering",
        skills="coding",
        picture="default.jpeg",
        submit="True",
    )
    response = client.post('/client', data=form.data, headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 400
    assert response.json['error'] == "Invalid form data"


def test_client_profile_form_duplicate_username(
        client: FlaskClient, database: SQLAlchemy,
        app: Flask, user_and_token: tuple):
    """ Test client profile form with duplicate username """
    with app.app_context():
        user = User(
            username="uniqueuser2",
            email="testuser2@example.com",
            password="securepassword",
            phone_number="+1234567890",
            role="Artisan",
            location="Test Location",
            created_at=datetime.now(timezone.utc),
            image_file="default.jpeg"
        )
        database.session.add(user)
        database.session.commit()
    _, token = user_and_token
    form = ClientProfileForm(
        username="uniqueuser2",
        email="testuser@example.com",
        phone_number="+1234567890",
        location="Somewhere",
        specialization="Engineering",
        skills="coding",
        picture="default.jpeg",
        submit="True",
    )
    response = client.post('/client', data=form.data, headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 400
    assert response.json['error'] == "Invalid form data"


def test_client_profile_form_duplicate_email(
        client: FlaskClient, database: SQLAlchemy,
        app: Flask, user_and_token: tuple):
    """ Test client profile form with duplicate email """
    with app.app_context():
        # update with an already taken email
        user = User.query.filter_by(username="uniqueuser").first()
        print(user)

    _, token = user_and_token
    form = ClientProfileForm(
        username="uniqueuser",
        email="testuser2@example.com",
        phone_number="+1234567890",
        location="Somewhere",
        specialization="Engineering",
        skills="coding",
        picture="default.jpeg",
        submit="True",
    )
    response = client.post('/client', data=form.data, headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 400
    assert response.json['error'] == "Invalid form data"
