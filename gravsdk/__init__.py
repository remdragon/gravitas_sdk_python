import sys
from typing import *
import requests
import json
from urllib.parse import urlparse

from gravsdk import gravcrud

class GravError(Exception):
	"""
	# Exception Class: `GravError`
	Exception raised for general SDK errors
	
	|Attribute|Description|
	|-|-|
	|`responsetext`|Descriptive text of the error|
	"""
	def __init__(self, responsetext: str):
		self.message = f"API error: `{responsetext}`"
		super().__init__(self.message)

class GravAuthError(Exception):
	"""
	# Exception Class: `GravAuthError`
	
	The `GravAuthError` exception class is raised when invalid credentials are used or response received from the API is missing data
	
	|Attribute|Type|Description|
	|-|-|-|
	|`responsetext`|str|Descriptive text of the failed authentication attempt|
	
	## Usage:
	
	    raise GravAuthError('No user data received')
	"""
	def __init__(self, responsetext: str):
		self.message = f"Login error: `{responsetext}`"
		super().__init__(self.message)

class GravGeneralError(Exception):
	"""
	# Exception Class: GravGeneralError

	The `GravGeneralError` exception class is raised when general non-specific errors occur, such as passing an incorrectly typed variable or other user mistakes occur.

	|Attribute|Type|Description|
	|-|-|-|
	|`responsetext`|str|Descriptive text of the error encountered|
	
	## Usage:
	
	    raise GravGeneralError('Invalid method specified: sdk.PUPPIES')

	"""
	def __init__(self, responsetext: str):
		self.message = f"General error: `{responsetext}`"
		super().__init__(self.message)

class sdkv1(object):
	"""
	# Gravitas Python SDK v1
	This is version 1 of the gravitas SDK. This includes the legacy/compatibility implementation of Gravitas.
	
	|Attribute|Required|Type|Description|
	|-|-|-|-|
	|`hoststring`|Required|string|Host connect string
	|`protocol`|Optional|string|Protocol used for communication with the Gravitas API server. Options are `https` and `wss` (defaults to `https`).
	|`port`|Optional|integer|Port number of the Gravitas API server (defaults to `443`)|
	|`ssl_verify_enable`|Optional|boolean|Enables/disables SSL certificate verification (defaults to `True`). **NOTE: in production this must remain as `True`**
	
	## Usage
	
	    from gravsdk import sdkv1
	    sdk = sdkv1(
	        hoststring = 'https://10.10.10.10:4443', # The port is optional
	        ssl_verify_enable = False # This should be `True` in production
	    )
	"""
	# CONSTANTS
	READ = 1
	CREATE = 2
	UPDATE = 3
	DELETE = 4 

	def __init__(self, hoststring: str, ssl_verify_enable: bool = True):
		try:
			self.hostparts = urlparse(hoststring)
		except Exception as e:
			raise GravError(f'invalid url specified: `{e}`')
		self.ssl_verify_enable = ssl_verify_enable
		self.protocol = self.hostparts.scheme
		#TODO FIXME: make this cleaner with enum
		if self.protocol == 'https':
			self.CRUD = gravcrud.HTTPCRUD(
				self.hostparts.geturl(),
				self.ssl_verify_enable,
			)
		#elif self.protocol == 'wss':
		#	self.CRUD = gravcrud.WSCRUD(
		#		self.hostparts.geturl(),
		#		self.ssl_verify_enable
		#	)
		else:
			raise GravError('invalid protocol specified, must be `https` or `wss`')

	def _login_sanity_check(self, result: bool, responsedata: Dict[str, str]) -> bool:
		if not result:
			raise GravAuthError('Invalid API data received')
		try:
			success = responsedata['success']
		except KeyError:
			raise GravAuthError ( 'api response missing `success` key' )
		if not success:
			# API authentication call was not successful
			raise GravAuthError(responsedata['error'])
		return True
	
	def login_session_check(self) -> Tuple[bool,Dict[str,str]]:
		"""
		# `login_session_check` SDK method

		The `login_session_check` SDK method checks the current user's logged in status. returns a tuple with the following information:
		
		## Expected return value format

		A tuple with the following information is returned:

		* A boolean that represents whether or not the user is logged in
		* A dictionary with user information (if logged in):

		|Attribute|Type|Description|Example|
		|-|-|-|-|
		|`FORCE_PWD_CHANGE`|boolean|Determines if user is forced to change their password|`False`|
		|`LAST_ACCT`|integer|The last account that this user accessed|`1`|
		|`NEXT_PWNED`|??? or `None`|TODO FIXME: get description for this|`None`|
		|`PWD_EXPIRE`|string (formatted as `YYYY-MM-DD` date)|Date that the user's password expires|`2020-10-23`|
		|`ROOT`|boolean|The administrative status of the user|`True`|
		|`USER`|string|The username of the user|`restuser`|
		|`USER_ID`|integer|The user ID number of the user|`2`|
		|`expired_pwd`|boolean|Whether or not the user's password is expired|`False`|

		## Usage

		    status, userdata = sdk.login_session_check()
		"""
		result, responsedata = self.CRUD.read('login', {})
		if not self._login_sanity_check(result, responsedata):
			return False, {}
		if len(responsedata['rows']) == 0:
			return False, {}
		else:
			return True, responsedata['rows'][0]
		
	
	def login(self, username: str, password: str) -> bool:
		"""
		# `login` SDK method
		
		The `login` SDK method is used to log in and establish a session with the Gravitas API server
		
		|Attribute|Required|Type|Description|
		|-|-|-|-|
		|`username`|yes|string|Username of the user to be logged in|
		|`password`|yes|string|Password of the user to be logged in|
		
		## Expected return value format
		
		The expected return value format is `bool` to indicate the success or failure of the login.
		
		## Usage
		
		    success = sdk.login(
		        username = 'restuser',
		        password = 'gravitas1234567890'
		    )
		"""
		payload = {
			'USER' : username,
			'PASSWORD' : password
		}
		result, responsedata = self.CRUD.create('login', payload)
		if not self._login_sanity_check(result, responsedata):
			return False
		if 'rows' not in responsedata:
			# For some reason we didn't receive any info for the user
			raise GravAuthError('No user data received')
		rows = responsedata['rows'][0]
		force_pwd_change = rows.get ( 'FORCE_PWD_CHANGE', False )
		if force_pwd_change:
			# Password must be changed
			raise GravAuthError(f'Password must be changed. Please log in with a browser to https://{self.hostparts.netloc} to change your password')
		if rows['expired_pwd']:
			# Password has expired
			raise GravAuthError(f'Password has expired. Please log in with a browser to https://{self.hostparts.netloc} to change your password')
		#TODO FIXME: deal with other scenarios
		return True

	def logout(self) -> bool:
		"""
		# `logout` SDK method
		
		The `logout` SDK method is used to perform a logout for the currently logged in user.
		
		## Expected return value format
		
		The expected return value format is `bool` to indicate the success or failure of the logout attempt.
		
		## Usage
		
		    success = sdk.logout()
		"""
		result, responsedata = self.CRUD.delete('login', {})
		if not self._login_sanity_check(result, responsedata):
			return False
		return True
	
	def clients(
		self,
		method: int,
		client_id: int = 0,
		fields: list = [],
		order: list = [],
		limit: int = 100,
		data: Dict[str,str] = {}
	) -> Dict[str,str]:
		"""
		# The `clients` SDK method
		
		The `clients` SDK method is used to get information about clients as well as set attributes for clients.

		The `clients` SDK method has 4 submethods:

		## `CREATE`

		Not Implemented Yet

		## `READ`

		|Attribute|Required|Type|Description|
		|-|-|-|-|
		|`method`|required|callable|method of request. One of `sdkv1.READ`, `sdkv1.UPDATE`, `sdkv1.CREATE`, `sdkv1.DELETE`|
		|`fields`|optional|list|List of fields to return in the search results. Default is to return all fields|
		|`order`|optional|list|List of fields to order the returned data by. Ignored if client_id is specified|
		|`client_id`|integer|Number 1-9999. Used to get information about a specific client|
		|`limit`|integer|Maximum number of results to return. Default is to return all results|
		
		## Expected return value format
		
		A tuple with the following information is returned:

		* A boolean that represents whether or not the request was successful
		* An array of dictionaries with client information. If a client_id is specified, a single element is returned
		
		## Usage
		
		    success, client_info = sdk.clients(
		        method = sdk.READ
				client_id = 100
				fields = [
					'CLIENT_ID',
					'NAME'
				],
				order = [
					'NAME'
				]
		        limit = 100
		    )

		## `UPDATE`
		
		Not Implemented Yet
		
		## `DELETE`

		Not Implemented Yet

		API NOTES:
		URL parameters don't appear to be functional:
		`limit` doesn't appear to do anything
		`fields` doesn't appear to do anything
		`order` doesn't appear to do anything
		"""
		if method not in [self.CREATE, self.READ, self.UPDATE, self.DELETE]:
			raise GravGeneralError(f'Invalid method specified: {method}')
		if method in [self.CREATE, self.UPDATE, self.DELETE]:
			raise GravGeneralError(f'Method not implemented yet!')
		if method == self.READ:
			params = {}
			if len(fields) > 0:
				params['fields'] = ','.join(fields)
			if limit > 0:
				params['limit'] = limit
			if len(order) > 0:
				params['order'] = ','.join(order)
			pathuri = "clients"
			if client_id > 0:
				pathuri = f"{pathuri}/{client_id}"
			success, responsedata = self.CRUD.read(pathuri, params)
			if not success:
				raise GravGeneralError(f"Error received from API: {responsedata['error']}")
			if len(responsedata['rows']) == 0:
				raise GravGeneralError(f"Client ID `{client_id}` not found!")
			return True, responsedata['rows']
