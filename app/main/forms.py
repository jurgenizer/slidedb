from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Email, Regexp
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField
from ..models import Role, User


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
               'Usernames must have only letters, numbers, dots or '
               'underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class CaseForm(FlaskForm):
    case_number = StringField('Case number', validators=[
        DataRequired(), Length(1, 3),
        Regexp('^[0-9]*$', 0, 'Only numbers please')])
    body = PageDownField('Case text', validators=[DataRequired()])
    slide_path = StringField('Slide path (URL)', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
class DeleteCaseForm(FlaskForm):
    case_number = StringField('Case number')
    body = StringField('Case text')
    slide_path = StringField('Slide path (URL)')
    submit = SubmitField('Delete')


class AnswerForm(FlaskForm):
    body = StringField('Your diagnosis:', validators=[DataRequired()])
    submit = SubmitField('Submit')
    
    
class RejoinderForm(FlaskForm):
    body = StringField('Your reply:', validators=[DataRequired()])
    submit = SubmitField('Submit')