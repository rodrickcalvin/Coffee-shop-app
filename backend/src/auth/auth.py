import json
from flask import request, _request_ctx_stack, abort
from functools import wraps
from jose import jwt
from urllib.request import urlopen
from os import environ


# AuthError Exception
'''
AuthError Exception
A standardized way to communicate auth failure modes
'''


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


# Auth Header
def get_token_auth_header():
    '''
        - Method attempts to get the header from the request and
        raises an AuthError if no header is present
        = it attempts to split bearer and the token and
        raises an AuthError if the header is malformed
        return the token part of the header
    '''
    auth = request.headers.get('Authorization', None)
    # check for header
    if not auth:
        raise AuthError({
            'code': 'authorization_header_missing',
            'description': 'Authorization header is expected.'
        }, 401)

    # split the bearer and the token:
    header_parts = auth.split()
    # check for the word "Bearer" just to make sure it is indeed a bearer token
    if header_parts[0].lower() != 'bearer':
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization header must start with "Bearer".'
        }, 401)

    # check if the header has less than two parts once it is split
    elif len(header_parts) == 1:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Token not found.'
        }, 401)
    # check if header is more than 2 parts
    elif len(header_parts) > 2:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization header must be bearer token.'
        }, 401)

    token = header_parts[1]
    return token


def check_permissions(permission, payload):
    '''
    - Takes in the specific @INPUTS:
        - permission: string permission (i.e. 'post:drink')
        - payload: decoded jwt payload

    - Raises an AuthError if permissions are not included in the payload
    - Raises an AuthError if the requested permission string is not in the
    payload permissions array
    - return true otherwise
    '''

    # check if there is a permissions 🗝️key in payload from the frontend
    if 'permissions' not in payload:
        raise AuthError({
            'code': 'invalid_claims',
            'description': 'Permissions not included in JWT.'
        }, 400)

    # check if the permission attached to the permissions key
    # is among the known app permissions
    if permission not in payload['permissions']:
        raise AuthError({
            'code': 'unauthorized',
            'description': 'Permission not found.'
        }, 401)

    return True


def verify_decode_jwt(token):
    '''
    - Takes in the @INPUT:
        token: a json web token (string)

        * should be an Auth0 token with key id (kid)
        * should verify the token using Auth0 /.well-known/jwks.json
        * should decode the payload from the token
        * should validate the claims
        and return the decoded payload
    '''

    json_url = urlopen(
        f'https://{environ["AUTH0_DOMAIN"]}/.well-known/jwks.json'
    )
    jwks = json.loads(json_url.read())
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}

    if 'kid' not in unverified_header:
        raise AuthError({
            'code': 'invalid_header',
            'description': 'Authorization malformed.'
        }, 401)

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=environ["ALGORITHMS"],
                audience=environ["API_AUDIENCE"],
                issuer='https://' + environ["AUTH0_DOMAIN"] + '/'
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError({
                'code': 'token_expired',
                'description': 'Token expired.'
            }, 401)

        except jwt.JWTClaimsError:
            raise AuthError({
                'code': 'invalid_claims',
                'description': 'Incorrect claims. Please, check the audience and issuer.'
            }, 401)
        except Exception:
            raise AuthError({
                'code': 'invalid_header',
                'description': 'Unable to parse authentication token.'
            }, 400)
    raise AuthError({
                'code': 'invalid_header',
                'description': 'Unable to find the appropriate key.'
            }, 400)


def requires_auth(permission=''):
    '''
    - Takes in the @INPUT
        permission: string permission (i.e. 'post:drink')

    - Uses the get_token_auth_header method to get the token
    - Uses the verify_decode_jwt method to decode the jwt
    - Uses the check_permissions method validate claims and check the
    requested permission
    - Returns the decorator which passes the decoded payload
    to the decorated method
    '''
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()

            payload = verify_decode_jwt(token)

            check_permissions(permission, payload)

            return f(payload, *args, **kwargs)
        return wrapper
    return requires_auth_decorator
