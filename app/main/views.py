from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, CaseForm,\
    AnswerForm, DeleteCaseForm, RejoinderForm
from .. import db
from ..email import send_email
from ..models import Permission, Role, User, Case, Answer,\
    Rejoinder
from ..decorators import admin_required, permission_required


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['SLIDEDB_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down, goodbye...'



@main.route('/', methods=['GET', 'POST'])
# the below permision added to hide data from ungegistered users
@permission_required(Permission.WRITE)
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Case.query.order_by(Case.case_number.asc()).paginate(
        page, per_page=current_app.config['SLIDEDB_CASES_PER_PAGE'],
        error_out=False)
    cases = pagination.items
    return render_template('index.html', cases=cases,
                           pagination=pagination)
                           
                           
@main.route('/case', methods=['GET', 'POST'])
# the below permision added to hide data from ungegistered users
@permission_required(Permission.WRITE)
def add_case():
    form = CaseForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        case = Case(case_number=form.case_number.data,
                    body=form.body.data,
                    slide_path=form.slide_path.data,
                    author=current_user._get_current_object())
        db.session.add(case)
        db.session.commit()
        flash('The case has been inserted into the database.')
        return redirect(url_for('.add_case'))
    
    page = request.args.get('page', 1, type=int)
    # old ordering of cases
    pagination = Case.query.order_by(Case.timestamp.desc()).paginate(
    page, per_page=1,
    error_out=False)
   
    cases = pagination.items
    return render_template('add_case.html', form=form, cases=cases,
                           pagination=pagination)



@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    # old ordering of cases
    #pagination = user.cases.order_by(Case.timestamp.desc()).paginate(
    #page, per_page=current_app.config['SLIDEDB_cases_PER_PAGE'],
    #error_out=False)
    # new ordering of cases
    pagination = user.cases.order_by(Case.case_number.asc()).paginate(
        page, per_page=1,
        error_out=False)
    cases = pagination.items
    return render_template('user.html', user=user, cases=cases,
                           pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/case/<int:id>', methods=['GET', 'POST'])
@login_required
def case(id):
    case = Case.query.get_or_404(id)
    form = AnswerForm()
    if form.validate_on_submit():
        answer = Answer(body=form.body.data,
                          case=case,
                          author=current_user._get_current_object())
        db.session.add(answer)
        db.session.commit()
        flash('Your diagnosis has been added to the database.') 
        
        #email functionality added by jurgen, email prof & admin
        send_email(current_app.config['SLIDEDB_PROF'], 'A student diagnosis from UCT PathSlides',
                   '/mail/answer', case=case, form=form, user=current_user._get_current_object())
        send_email(current_app.config['SLIDEDB_ADMIN'], 'A student diagnosis from UCT PathSlides',
                   '/mail/answer', case=case, form=form, user=current_user._get_current_object())
            
        flash('Your diagnosis has been emailed for comment.')
        #email functionality added by jurgen

        return redirect(url_for('.case', id=case.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (case.answers.count() - 1) // \
            current_app.config['SLIDEDB_ANSWERS_PER_PAGE'] + 1
    pagination = case.answers.order_by(Answer.timestamp.desc()).paginate(
        page, per_page=current_app.config['SLIDEDB_ANSWERS_PER_PAGE'],
        error_out=False)
    answers = pagination.items
    return render_template('case.html', cases=[case], form=form,
                           answers=answers,pagination=pagination)    
                           


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    case = Case.query.get_or_404(id)
    if current_user != case.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    form = CaseForm()
    if form.validate_on_submit():
        case.body = form.body.data
        db.session.add(case)
        db.session.commit()
        flash('The case has been updated.')
        return redirect(url_for('.case', id=case.id))
    form.case_number.data = case.case_number
    form.body.data = case.body
    form.slide_path.data = case.slide_path
    return render_template('edit_case.html', form=form)
    
# added by jurgen to delete a case
@main.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(id):
    case = Case.query.get_or_404(id)
    if current_user != case.author and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    form = DeleteCaseForm()
    if form.validate_on_submit():
        db.session.delete(case)
        db.session.commit()
        flash('The case (case) has been deleted.')
        return redirect(url_for('.index'))
    form.case_number.data = case.case_number
    form.body.data = case.body
    form.slide_path.data = case.slide_path
    return render_template('delete_case.html', form=form)
# added by jurgen to delete a case



# added by jurgen to respond to a answer(rejoinder) 
@main.route('/rejoinder/<int:id>', methods=['GET', 'POST'])
@login_required
def rejoinder(id):
    answer = Answer.query.get_or_404(id)
    if current_user != answer.author and \
            not current_user.can(Permission.MODERATE):
        abort(403)
    form = RejoinderForm()
    if form.validate_on_submit():
        rejoinder = Rejoinder(body=form.body.data,
                          answer=answer,
                          author=current_user._get_current_object())
        db.session.add(rejoinder)
        db.session.commit()

        flash('Reply submitted.')
        
        #email functionality added by jurgen
        if current_user == answer.author and \
            not current_user.can(Permission.MODERATE):
            send_email(current_app.config['SLIDEDB_PROF'], 'A reply from UCT PathSlides',
                   '/mail/rejoinder', answer=answer, form=form, user=current_user._get_current_object())
            
            
        if current_user.can(Permission.MODERATE):
            answer_author_email = answer.author.email
            send_email(answer_author_email, 'A reply from UCT PathSlides',
                   '/mail/rejoinder', answer=answer, form=form, user=current_user._get_current_object())

            
        flash('Your reply has been emailed.')
        #email functionality added by jurgen
        
        return redirect(url_for('.case', id=answer.case.id))

    return render_template('rejoinder_answer.html', answers=[answer], form=form)
# added by jurgen to respond to a answer(rejoinder) 

    
    
@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Answer.query.order_by(Answer.timestamp.desc()).paginate(
        page, per_page=current_app.config['SLIDEDB_ANSWERS_PER_PAGE'],
        error_out=False)
    answers = pagination.items
    return render_template('moderate.html', answers=answers,
                           pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    answer = Answer.query.get_or_404(id)
    answer.disabled = False
    db.session.add(answer)
    db.session.commit()
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    answer = Answer.query.get_or_404(id)
    answer.disabled = True
    db.session.add(answer)
    db.session.commit()
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))
                            
@main.route('/moderate/delete/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_delete(id):
    answer = Answer.query.get_or_404(id)
    db.session.delete(answer) 
    db.session.commit()
    flash('The diagnosis has been deleted.')
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))
                            
@main.route('/moderate/deleter/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
def moderate_deleter(id):
    #Answer = Answer.query.get_or_404(id)
    rejoinder = Rejoinder.query.get_or_404(id)
    db.session.delete(rejoinder) 
    db.session.commit()
    flash('The reply has been deleted.')
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))



