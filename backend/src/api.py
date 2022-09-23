import os
from flask import Flask, request, jsonify, abort
from sqlalchemy import exc
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink
from .auth.auth import AuthError, requires_auth

# create and configure the app
app = Flask(__name__)
setup_db(app)
CORS(app)

'''
The following line initializes the database
!! NOTE THIS WILL DROP ALL RECORDS AND START YOUR DB FROM SCRATCH
!! Running this funciton will add one
'''
db_drop_and_create_all()

# ROUTES


@app.route('/drinks')
def get_drinks():
    '''
    GET /drinks
        - Is a public endpoint
        - Contains only the drink.short() data representation
        - returns status code 200 and json {"success": True, "drinks": drinks}
        where drinks is the list of drinks
        or appropriate status code indicating reason for failure
    '''

    # Fetch all drinks from the db
    drinks = Drink.query.all()

    # Loop through all the items and make them summarized
    drinks_summary = [drink.short() for drink in drinks]

    return jsonify({
        'success': True,
        'drinks': drinks_summary
    }), 200


@app.route('/drinks-detail')
@ requires_auth('get:drinks-detail')
def get_drinks_detail(payload):
    '''
    GET /drinks-detail
        - Requires the 'get:drinks-detail' permission
        - Contains the drink.long() data representation
        - returns status code 200 and json {"success": True, "drinks": drinks}
        where drinks is the list of drinks or appropriate status code
        indicating reason for failure
    '''
    # Fetch all drinks from the db
    drinks = Drink.query.all()

    # Loop through all the items and retrieve their details
    drinks_details = [drink.long() for drink in drinks]

    return jsonify({
        'success': True,
        'drinks': drinks_details
    }), 200


@app.route('/drinks', methods=['POST'])
@ requires_auth('post:drinks')
def create_drink(payload):
    '''
    POST /drinks
        - Creates a new row in the drinks table
        - Requires the 'post:drinks' permission
        - Contains the drink.long() data representation
        - returns status code 200 and json {"success": True, "drinks": drink}
        where drink an array containing only the newly created drink
        or appropriate status code indicating reason for failure
    '''

    body = request.get_json()

    try:
        # Create new drink
        new_title = body.get('title', None)
        new_recipe = body.get('recipe', None)

        # Abort if tile or recipe are missing
        if (
            new_title is None or
            new_recipe is None
        ):
            abort(422)

        # Create instance of Drink model
        new_drink = Drink(title=new_title, recipe=json.dumps(new_recipe))
        new_drink.insert()

        return jsonify({
            'success': True,
            'drinks': [new_drink.long()]
        }, 200)
    except Exception as e:
        print(e)
        abort(422)


@app.route('/drinks/<int:id>', methods=['PATCH'])
@ requires_auth('patch:drinks')
def update_drink(paylaod, id):
    '''
    PATCH /drinks/<id>
        where <id> is the existing model id
        - Responds with a 404 error if <id> is not found
        - Updates the corresponding row for <id>
        - Requires the 'patch:drinks' permission
        - Contains the drink.long() data representation
        - returns status code 200 and json {"success": True, "drinks": drink}
        where drink an array containing only the updated drink
        or appropriate status code indicating reason for failure
    '''

    body = request.get_json()

    try:
        # Recieve the updated columns of Drink model
        updated_title = body.get('title', None)
        updated_recipe = body.get('recipe', None)

        # Get specific Drink by ID
        drink = Drink.query.filter(Drink.id == id).one_or_none()

        # Abort if specific drink doesn't exist
        if drink is None:
            abort(404)

        # Check if the user has updated the values
        if updated_title:
            drink.title = updated_title

        if updated_recipe:
            drink.recipe = json.dumps(updated_recipe)

        # Alter the db
        drink.update()

        return jsonify({
            'success': True,
            'drinks': [drink.long()]
        }, 200)
    except Exception as e:
        print(e)
        abort(422)


@app.route('/drinks/<int:id>', methods=['DELETE'])
@ requires_auth('delete:drinks')
def delete_drink(payload, id):
    '''
    DELETE /drinks/<id>
        where <id> is the existing model id
        - Responds with a 404 error if <id> is not found
        - Deletes the corresponding row for <id>
        - Requires the 'delete:drinks' permission
        - returns status code 200 and json {"success": True, "delete": id}
        where id is the id of the deleted record
        or appropriate status code indicating reason for failure
    '''

    try:
        # Get specific Drink by ID
        drink = Drink.query.filter(Drink.id == id).one_or_none()

        # # Abort if specific drink doesn't exist
        if drink is None:
            abort(404)

        # delete specific drink from the db
        drink.delete()

        return jsonify({
            'success': True,
            'delete': id
        }, 200)
    except:
        abort(422)


# Error Handling
@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
        "success": False,
        "error": 422,
        "message": "unprocessable"
    }), 422


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": 404,
        "message": "resource not found"
    }), 404


@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": 400,
        "message": "bad request"
    }), 400


@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "success": False,
        "error": 500,
        "message": "internal server error"
    }), 500


@app.errorhandler(AuthError)
def auth_error(error):
    return jsonify({
        "success": False,
        "error": error.status_code,
        "message": error.error
    }), error.status_code
