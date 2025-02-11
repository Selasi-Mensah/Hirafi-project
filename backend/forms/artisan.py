#!/usr/bin/env python3
"""
Contains Artisan's profile form
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Email, ValidationError
from models.user import User
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from geopy.geocoders import Nominatim


class ArtisanProfileForm(FlaskForm):
    """ This form for Artisan Profile:
    fields:
        - username
        - email
        - phone_number
        - location
        - specialization
        - skills
        - salary_per_hour
        - picture
        - submit
    methods:
        - validate_username
        - validate_email
        - validate_on_submit
    """
    username = StringField('Username', validators=[
                                DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[
                            DataRequired(), Email()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    location = StringField('Location', validators=[
        DataRequired(),
        Length(
            min=2, max=100,
            message="Location must not exceed 60 characters."
            )
        ])
    # Specialization selection in frontend
    specialization = StringField('Specialization', validators=[DataRequired()])
    skills = TextAreaField('Skills', validators=[
        Length(
            max=500,
            message="Skills description must not exceed 500 characters.")])

    salary_per_hour = StringField(
        'Salary per Hour', validators=[DataRequired()],
        render_kw={"type": "number", "step": "0.1"})

    picture = FileField(
        'Update Profile Picture',
        validators=[FileAllowed(['jpg', 'jpeg', 'png'])])

    # submit = SubmitField('Update')

    def validate_username(self, username: StringField) -> None:
        """ method to validate username """
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=user_id).first()
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username is already taken!')

    def validate_email(self, email: StringField) -> None:
        """ method to validate password """
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        current_user = User.query.filter_by(id=user_id).first()
        if email.data.lower() != current_user.email:
            user = User.query.filter_by(email=email.data.lower()).first()
            if user:
                raise ValidationError('Email is already taken!')

    def validate_location(self, location: StringField) -> None:
        """ method to validate location """
        geolocator = Nominatim(user_agent="Hirafic_Project/1.0", timeout=10)
        location = geolocator.geocode(location.data)
        if location is None:
            raise ValidationError("This location could not be found")
