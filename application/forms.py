from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, ValidationError, URL

import pgeocode
import pandas
import json


class NewUserForm(FlaskForm):
    ''' form for adding a new user '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.country.choices = self.get_country_choices()


    @staticmethod
    def get_country_choices():
        country_choices = []

        data = load_country_codes()
        keys = list(data.keys())
        if keys:
            for key in keys:
                country_choices.append((key, key))
        return country_choices
    

    def validate_zipcode(self, zipcode):
        if not check_zipcode(zipcode.data, self.country.data):
            raise ValidationError('Invalid zipcode for the selected country.')

    name = StringField('Full Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired(), Length(max=15)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    country = SelectField('Country', validators=[DataRequired()])
    zipcode = StringField('Zipcode', validators=[DataRequired(), Length(min=5,max=5), validate_zipcode])
    bio = TextAreaField('Bio', validators=[Length(max=100)])
    profile_img = StringField('profile_img')


class LoginForm(FlaskForm):
    ''' form for user to login '''
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])


class EditUserForm(FlaskForm):
    ''' form for editing user details '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.country.choices = self.get_country_choices()


    @staticmethod
    def get_country_choices():
        country_choices = []

        data = load_country_codes()
        keys = list(data.keys())
        if keys:
            for key in keys:
                country_choices.append((key, key))
        return country_choices
    

    def validate_zipcode(self, zipcode):
        if not check_zipcode(zipcode.data, self.country.data):
            raise ValidationError('Invalid zipcode for the selected country.')
        
    name = StringField('Full Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired(), Length(max=15)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    country = SelectField('Country', validators=[DataRequired()])
    zipcode = StringField('Zipcode', validators=[DataRequired(), Length(min=5,max=5), validate_zipcode])
    bio = TextAreaField('Bio', validators=[Length(max=100)])


class ChangePasswordForm(FlaskForm):
    password = PasswordField('Old Password', validators=[DataRequired(), Length(min=6)])

    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), Length(min=6)])


class ChangePfpForm(FlaskForm):
    profile_img = StringField('profile_img')


def check_zipcode(zipcode, country):
    load_cc = load_country_codes()
    cc = load_cc.get(country) 
    nomi = pgeocode.Nominatim(cc)
    data = nomi.query_postal_code(zipcode)

    if data is not None and not pandas.isna(data['latitude']) and not pandas.isna(data['longitude']):
        return True
    return False


def load_country_codes(file_path='data/countries.json'):
    with open(file_path, 'r') as file:
        return json.load(file)

