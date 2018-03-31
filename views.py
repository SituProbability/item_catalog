#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is to create an application that provides a list of items
# within a variety of categories as well as provide a user registration
# and authentication system. Registered users will have the ability to post,
# edit and delete their own items.

from flask import Flask, render_template, url_for, flash, \
     redirect, request, jsonify

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from models import Base, Category, ListItem, User

from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
import bleach


app = Flask(__name__)
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;\
        border-radius: 150px;-webkit-border-radius: 150px;\
        -moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['user_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        flash('You have successfully been logged out.')
        return redirect(url_for('showCategories'))
    else:
        # For whatever reason, the given token was invalid.
        flash("Failed to revoke token for given user.")
        return redirect(url_for('showCategories'))


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# JSON APIs to view Catalog Information
@app.route('/category/JSON')
def categoriesJSON():
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).all()
    return jsonify(categories=[c.serialize for c in categories])

@app.route('/items/JSON')
def itemsJSON():
    if 'username' not in login_session:
        return redirect('/login')
    items = session.query(ListItem).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/category/<int:category_id>/items/JSON')
def categoryListJSON(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    items = session.query(ListItem).filter_by(category_id=category_id).all()
    return jsonify(ListItems=[i.serialize for i in items])


@app.route('/category/<int:category_id>/items/<int:item_id>/JSON')
def itemJSON(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    item = session.query(ListItem).filter_by(id=item_id).one()
    return jsonify(item=item.serialize)


# Show all categories
@app.route('/')
@app.route('/category/')
def showCategories():
    categories = session.query(Category).order_by(desc(Category.id))
    category = categories.first()
    if category is None:
        category_id = 1
    else:
        category_id = category.id
    items = session.query(ListItem).order_by(desc(ListItem.id))
    if 'username' not in login_session:
        return render_template('publiccategories.html',
                               categories=categories,
                               items=items,
                               category_id=category_id)
    else:
        username = login_session['username']
        picture = login_session['picture']
        return render_template('categories.html',
                               categories=categories,
                               items=items,
                               category_id=category_id,
                               username=username,
                               picture=picture)


# Create a new category
@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(name=bleach.clean(request.form['name']),
                               user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New Category %s Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newCategory.html')


# Edit a category
@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedCategory = session.query(Category).filter_by(id=category_id).one()
    if editedCategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
to edit this restaurant. Please create your own restaurant in order \
to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = bleach.clean(request.form['name'])
            session.add(editedCategory)
            session.commit()
            flash('Category Successfully Edited %s' % editedCategory.name)
            return redirect(url_for('showList', category_id=category_id))
    else:
        return render_template('editCategory.html',
                               category=editedCategory,
                               category_id=category_id)


# Delete a category
@app.route('/category/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categoryToDelete = session.query(Category).filter_by(id=category_id).one()
    itemsToDelete = session.query(ListItem).filter_by(category_id=category_id
                                                      ).all()
    if categoryToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
to edit this restaurant. Please create your own restaurant in order \
to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(categoryToDelete)
        for item in itemsToDelete:
            session.delete(item)
        session.commit()
        flash('%s Successfully Deleted' % categoryToDelete.name)
        return redirect(url_for('showCategories', category_id=category_id))
    else:
        return render_template('deleteCategory.html',
                               category=categoryToDelete,
                               category_id=category_id)


# Show a category list
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/list/')
def showList(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    categories = session.query(Category).order_by(desc(Category.id))
    items = session.query(ListItem).filter_by(category_id=category_id
                                              ).order_by(desc(ListItem.id))
    creator = getUserInfo(category.user_id)
    if 'username' not in login_session:
        return render_template('publiclist.html',
                               items=items,
                               category=category,
                               categories=categories,
                               category_id=category_id,
                               creator=creator)
    if 'username' not in login_session \
       or creator.id != login_session['user_id']:
        return render_template('categorylist.html',
                               items=items,
                               category=category,
                               categories=categories,
                               category_id=category_id,
                               creator=creator)
    else:
        return render_template('showlist.html',
                               items=items,
                               category=category,
                               categories=categories,
                               category_id=category_id,
                               creator=creator)


# Show a list item
@app.route('/category/<int:category_id>/item/<int:item_id>/')
def showListItem(category_id, item_id):
    item = session.query(ListItem).filter_by(id=item_id).one()
    creator = getUserInfo(item.user_id)
    if 'username' not in login_session \
       or creator.id != login_session['user_id']:
        return render_template('publiclistitem.html',
                               item=item,
                               category_id=category_id,
                               item_id=item_id,
                               creator=creator)
    else:
        return render_template('showlistitem.html',
                               item=item,
                               category_id=category_id,
                               item_id=item_id,
                               creator=creator)


# Create a new item
@app.route('/category/<int:category_id>/item/new/', methods=['GET', 'POST'])
def newListItem(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category)
    if request.method == 'POST':
        category_name = request.form['category']
        category = session.query(Category).filter_by(name=category_name).one()
        newItem = ListItem(name=bleach.clean(request.form['name']),
                           description=bleach.clean(request.form['description']),
                           category_id=category.id,
                           user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash('New Item %s Successfully Created' % (newItem.name))
        return redirect(url_for('showList',
                                categories=categories,
                                category_id=category.id))
    else:
        return render_template('newlistitem.html',
                               categories=categories,
                               category_id=category_id)


# Edit a list item
@app.route('/category/<int:category_id>/item/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editListItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category)
    editedItem = session.query(ListItem).filter_by(id=item_id).one()
    category = session.query(Category).filter_by(id=category_id).one()
    if editedItem.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
to edit this restaurant. Please create your own restaurant in order \
to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = bleach.clean(request.form['name'])
        if request.form['description']:
            editedItem.description = bleach.clean(request.form['description'])
        if request.form['description']:
            category_name = request.form['category']
            category = session.query(Category).filter_by(
                name=category_name).one()
            editedItem.category_id = category.id
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showList',
                                categories=categories,
                                category_id=category.id))
    else:
        return render_template('editlistitem.html',
                               category_id=category_id,
                               item_id=item_id,
                               categories=categories,
                               item=editedItem)


# Delete a list item
@app.route('/category/<int:category_id>/item/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteListItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category)
    itemToDelete = session.query(ListItem).filter_by(id=item_id).one()
    if itemToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
to edit this restaurant. Please create your own restaurant in order \
to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showList',
                                categories=categories,
                                category_id=category_id))
    else:
        return render_template('deletelistitem.html',
                               item=itemToDelete,
                               category_id=category_id)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.static_folder = 'static'
    app.run(host='0.0.0.0', port=8000)
