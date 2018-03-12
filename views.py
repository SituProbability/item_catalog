from flask import Flask, render_template, url_for, flash, redirect, request, jsonify

from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from models import Base, Category, ListItem

from flask import session as login_session

app = Flask(__name__)

#Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


#Show all categories
@app.route('/')
@app.route('/category/')
def showCategories():
    categories = session.query(Category).order_by(desc(Category.id))
    category = categories.first()
    category_id = category.id
    items = session.query(ListItem).order_by(desc(ListItem.id))
    return render_template('categories.html', categories = categories, items=items, category_id=category_id)


#Create a new category
@app.route('/category/new/', methods=['GET','POST'])
def newCategory():
    if request.method == 'POST':
        newCategory = Category(name = request.form['name'])
        session.add(newCategory)
        flash('New Category %s Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newCategory.html')


#Edit a category
@app.route('/category/<int:category_id>/edit/', methods = ['GET', 'POST'])
def editCategory(category_id):
    editedCategory = session.query(Category).filter_by(id = category_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            session.add(editedCategory)
            session.commit()
            flash('Category Successfully Edited %s' % editedCategory.name)
            return redirect(url_for('showList', category_id=category_id))
    else:
        return render_template('editCategory.html', category=editedCategory, category_id=category_id)


#Delete a category
@app.route('/category/<int:category_id>/delete/', methods = ['GET','POST'])
def deleteCategory(category_id):
    categoryToDelete = session.query(Category).filter_by(id = category_id).one()
    itemsToDelete = session.query(ListItem).filter_by(category_id = category_id).all()
    if request.method == 'POST':
        session.delete(categoryToDelete)
        for item in itemsToDelete:
            session.delete(item)
        session.commit()
        flash('%s Successfully Deleted' % categoryToDelete.name)
        return redirect(url_for('showCategories', category_id = category_id))
    else:
        return render_template('deleteCategory.html',category = categoryToDelete, category_id=category_id)


# Show a category list
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/list/')
def showList(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    categories = session.query(Category).order_by(desc(Category.id))
    items = session.query(ListItem).filter_by(category_id=category_id).order_by(desc(ListItem.id))
    return render_template('showlist.html', items=items, category=category, categories=categories, category_id=category_id)


# Show a list item
@app.route('/category/<int:category_id>/item/<int:item_id>/')
def showListItem(category_id, item_id):
    item = session.query(ListItem).filter_by(id = item_id).one()    
    return render_template('showlistitem.html', item = item, category_id=category_id, item_id=item_id)
    

# Create a new item
@app.route('/category/<int:category_id>/item/new/', methods=['GET', 'POST'])
def newListItem(category_id):
    categories = session.query(Category)
    if request.method == 'POST':
        category_name = request.form['category']
        category = session.query(Category).filter_by(name=category_name).one()
        newItem = ListItem(name=request.form['name'], description=request.form['description'],
                           category_id=category.id)
        session.add(newItem)
        session.commit()
        flash('New Item %s Successfully Created' % (newItem.name))
        return redirect(url_for('showList', categories=categories, category_id=category.id))
    else:
        return render_template('newlistitem.html', categories=categories, category_id=category_id)

#Edit a list item
@app.route('/category/<int:category_id>/item/<int:item_id>/edit', methods=['GET','POST'])
def editListItem(category_id, item_id):
    categories = session.query(Category)
    editedItem = session.query(ListItem).filter_by(id = item_id).one()
    category = session.query(Category).filter_by(id = category_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['description']:
            category_name = request.form['category']
            category = session.query(Category).filter_by(name=category_name).one()
            editedItem.category_id = category.id
        session.add(editedItem)
        session.commit() 
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showList', categories=categories, category_id=category.id))
    else:
        return render_template('editlistitem.html', category_id=category_id, item_id=item_id, categories=categories, item = editedItem)


#Delete a list item
@app.route('/category/<int:category_id>/item/<int:item_id>/delete', methods = ['GET','POST'])
def deleteListItem(category_id, item_id):
    categories = session.query(Category)
    itemToDelete = session.query(ListItem).filter_by(id = item_id).one() 
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showList', categories=categories, category_id=category_id))
    else:
        return render_template('deletelistitem.html', item = itemToDelete, category_id=category_id)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.static_folder = 'static'
    app.run(host = '0.0.0.0', port = 8000)
