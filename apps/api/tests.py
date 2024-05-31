from django.test import TestCase, RequestFactory
from rest_framework import status
import sys
import os

from apps.api.views import AuthView,LoginView
from apps.api.constants import ERROR_TYPES,RESPONSE_CODES
from apps.user_app.models import User
from apps.user_app.serializers import SimpleUserSerializer, UserSerializer

from apps.recipe_app.models import Recipe
from apps.recipe_app.serializers import RecipeSerializer

from datetime import datetime
import json


red_color = "\033[91m"  # ANSI escape code for red color
green_color = "\033[92m"  # ANSI escape code for green color
reset_color = "\033[0m"  # ANSI escape code to reset color

def print_green(str):
    print(f"{green_color}{str}{reset_color}")
    
def print_red(str):
    print(f"{red_color}{str}{reset_color}")
    
# ----------------------------------------------
# Section 1:  Helping Functions
# ----------------------------------------------
# 
# ----------------------------------------------
    
def login(factory,email,password):
        request = factory.post('/auth/login', data={
                                    "email":email,
                                    "password":password
                                    },
                                    content_type='application/json')
        view = LoginView.as_view()
        response = view(request)
        return response

def test_metadata(test_case,response_data):
    
        test_case.assertIn("_metadata", response_data)
        test_case.assertIn("page", response_data["_metadata"])  
        test_case.assertIn("page_size", response_data["_metadata"])  
        test_case.assertIn("total_pages", response_data["_metadata"])  
        test_case.assertIn("total_users", response_data["_metadata"])
        
def test_error(test_case,response_data,error_type):
    test_case.assertIn('error', response_data)
    test_case.assertIsInstance(response_data['error'], dict)
    test_case.assertIn(error_type, response_data['error'])


# ----------------------------------------------
# Section 1:  TestCases
# ----------------------------------------------
# 
# ----------------------------------------------


class AuthViewTestCase(TestCase):

        
    def setUp(self):
        self.factory = RequestFactory()
        
        self.total = 0
        self.success = 0
        self.error = 0
        
        self._test_user_password = 'password123' 
        
        self.test_user = User.objects.create_user(
            username='test_username',
            email='test@example.com',
            name='Test User',
            password= self._test_user_password,  # Set a secure password here
            birth_date=datetime(year=2000, month=1, day=1),  # Fill in the required fields
        )
        
        
        
        self.simple_user = None
        self.simple_user_data = {
            'username': 'test_register_username',
            'email': 'test_registe@example.com',
            'name': 'Test User',
            'password': 'password123',  # Set a secure password here
            'birth_date': "2000-03-15T00:00:00Z",  # Fill in the required fields
        }
        
    def test_register_user_simple(self):

        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.
        # ----------------------------------------------

        self.total += 1
        
        print("\n")
        print(f"Running: {self.test_register_user_simple.__name__}")
        print("\n")

        

        request = self.factory.post(
            '/auth', data=self.simple_user_data, content_type='application/json')
        
        view = AuthView.as_view()
        response = view(request)
        response.render()

        self.simple_user = json.loads(response.content.decode('utf-8'))

        # ----------------------------------------------
        # Section 2: Conection
        # ----------------------------------------------
        # Assert connection expectation.
        # ----------------------------------------------

        try:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.data}")
            return

        # ----------------------------------------------
        # Section 3: User ( simple )
        # ----------------------------------------------
        # Assert response expectation.
        # ----------------------------------------------
        

        
        try:
           # Check if all fields from simple_user_data are in response.data
            for field, value in self.simple_user_data.items():
                if field == 'password':
                    self.assertNotIn(field, self.simple_user, f"{field} is not missing in response data")
                else:
                    self.assertIn(field, self.simple_user, f"{field} is missing in response data")
                    self.assertEqual(self.simple_user[field], value, f"{field} value is incorrect")
            
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Test user (simple):\n{self.simple_user_data}\n")
            print(f"Response user:\n{self.test_user}")
            
        self.success+= 1
        print_green("\nSuccess")
            
    def test_login_user(self,silent = False):
        
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.
        # ----------------------------------------------
        
        
        
        if not silent:
            print("\n")
            print(f"Running: {self.test_login_user.__name__}")
            print("\n")
            
            self.total += 1
        
        response = login(factory = self.factory,
                              email = self.test_user.email,
                              password = self._test_user_password)
        
        # ----------------------------------------------
        # Section 2: Conection
        # ----------------------------------------------
        # Assert connection expectation.
        # ----------------------------------------------
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.data}")
            return
        
        # ----------------------------------------------
        # Section 3: Auth
        # ----------------------------------------------
        # Assert response expectation.
        # ----------------------------------------------
        
        expected_keys = ["refresh_token", "refresh_token_expires", "access_token", "access_token_expires"]
        
        try:
            
            for key in expected_keys:
                
                self.assertIn(key, response.data, f"{key} is missing in response data")
                self.assertTrue(response.data[key], f"{key} has an empty value")
                
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            
        if not silent:
            self.success+= 1
            print_green("\nSuccess")
        
        
        return response.data  
    
    def test_get_user(self):
        
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.
        # ----------------------------------------------

        print("\n")
        print(f"Running: {self.test_get_user.__name__}")
        print("\n")
        
        self.total += 1
        
        # Authenticate
        auth_token = self.test_login_user(silent =True)
        
        request = self.factory.get('/auth',HTTP_AUTHORIZATION=f'Bearer {auth_token["access_token"]}')
        view = AuthView.as_view()
        response = view(request)
        
        
        
        # ----------------------------------------------
        # Section 2: Conection
        # ----------------------------------------------
        # Assert connection expectation.
        # ----------------------------------------------
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.data}")
            return
        
        # ----------------------------------------------
        # Section 3: Auth
        # ----------------------------------------------
        # Assert response expectation.
        # ----------------------------------------------
        
        try:
            self.assertEqual(UserSerializer(self.test_user).data,UserSerializer(response.data).data, f"User's are different.")
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Expected User:\n{UserSerializer(self.test_user).data}\n")
            print(f"Response User:\n{UserSerializer(response.data).data}")
        
        print_green("\nSuccess")
        self.success+= 1
    
    def test_logout_user(self):
        
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.
        # ----------------------------------------------
        
        
        print("\n")
        print(f"Running: {self.test_logout_user.__name__}")
        print("\n")
        
        self.total += 1
        
        # Authenticate
        auth_token = self.test_login_user(silent =True)
        
        request = self.factory.delete('/auth',
                                      HTTP_AUTHORIZATION=f'Bearer {auth_token["access_token"]}',
                                      data={"refresh_token":auth_token["refresh_token"]},
                                      content_type='application/json')
        view = AuthView.as_view()
        response = view(request)
        
        # ----------------------------------------------
        # Section 2: Conection
        # ----------------------------------------------
        # Assert connection expectation.
        # ----------------------------------------------
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.data}")
            return
        
        # ----------------------------------------------
        # Section 3: Test auth after user logout TODO
        # ----------------------------------------------
        # Assert response expectation.
        # ----------------------------------------------
        
            
        self.success+= 1
        print_green("\nSuccess")


from apps.api.views import UserListView,UserView,UsersToFollowView,FollowView

from apps.user_app.constants import USER_MAX_WEIGHT,USER_MIN_WEIGHT,USER_MIN_HEIGHT,USER_MAX_HEIGHT,STRING_USER_BIRTHDATE_PAST_ERROR,STRING_USER_BIRTHDATE_YOUNG_ERROR

class UserViewTestCase(TestCase):
    
    
    def setUp(self):
        self.factory = RequestFactory()
        
        # General
        
        self.total = 0
        self.success = 0
        self.error = 0
        
        # Testing models
        
        self._test_user_password = 'password123' 
        
        self.test_user = User.objects.create_user(
            username='teste_user',
            email='teste_user@example.com',
            name='Test User',
            password=self._test_user_password,  # Set a secure password here
            birth_date=datetime(year=2000, month=1, day=1),  # Fill in the required fields
        )
        
        self._test_user_2_password = 'password123' 
        
        self.test_user_2 = User.objects.create_user(
            username='teste_user_2',
            email='teste_user_2@example.com',
            name='Test User 2',
            password=self._test_user_2_password,  # Set a secure password here
            birth_date=datetime(year=2000, month=1, day=1),  # Fill in the required fields
        )
        
        self._test_user_delete_password = 'password123' 
        
        self.test_user_delete = User.objects.create_user(
            username='test_user_delete',
            email='test_user_delete@example.com',
            name='Test User Delete',
            password=self._test_user_delete_password,  # Set a secure password here
            birth_date=datetime(year=2000, month=1, day=1),  # Fill in the required fields
        )
        
        
        
        
        # Get Auth Token
        
        self.auth = login(factory = self.factory,
                              email = self.test_user.email,
                              password = self._test_user_password).data

    def test_get_users(self):
        
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.

        print("\n")
        print(f"Running: {self.test_get_users.__name__}")
        print("\n")
        
        self.total += 1       
        
        
        # ----------------------------------------------
        # Section 2: Validations
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")

        # ----------------------------------------------
        # Section 2.1: No Args
        # ----------------------------------------------
        # This subsection contains tests for cases where no arguments are provided.
        
        print(f"Testing No Args")
        
        request = self.factory.get('/user/list',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = UserListView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.1.2: Result
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        
        # Test Metadata
        
        try:
            test_metadata(self,response_data)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # Test Result
        
        try:
            
            self.assertIn('result', response_data)
            self.assertIsInstance(response_data['result'], list)
            self.assertEqual(len(response_data['result']), 3)
            
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        try:
            self.assertEqual(SimpleUserSerializer(self.test_user).data,response_data['result'][0], f"User's are different.")
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Expected User:\n{UserSerializer(self.test_user).data}\n")
            print(f"Response User:\n{self.test_user}")
        

        

        
        print_green("\nSuccess")
        self.success+= 1

    
    def test_get_user(self):
        
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.

        print("\n")
        print(f"Running: {self.test_get_user.__name__}")
        print("\n")
        
        self.total += 1       
        
        
        # ----------------------------------------------
        # Section 2: Validations
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")

        # ----------------------------------------------
        # Section 2.1: No Args
        # ----------------------------------------------
        # This subsection contains tests for cases where no arguments are provided.
        
        print(f"Testing No Args")
        
        request = self.factory.get('/user',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = UserView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.1.2: Result
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        self.assertIn("error", response_data)
        self.assertIn("args", response_data["error"])    
        
        
        # ----------------------------------------------
        # Section 2.2: Id
        # ----------------------------------------------
        # Assert connection expectation.
        
        print(f"Testing whit Id")
        
        request = self.factory.get(f'/user?id={self.test_user_2.id}',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = UserView.as_view()
        response = view(request)
        response_data = response.data
        
        # ----------------------------------------------
        # Section 2.2.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.2.2: Result
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(SimpleUserSerializer(self.test_user_2).data,response_data, f"User's are different.")
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Expected User:\n{SimpleUserSerializer(self.test_user_2).data}\n")
            print(f"Response User:\n{response_data}")
        
        
        
        # ----------------------------------------------
        # Section 2.3: Username
        # ----------------------------------------------
        # Assert connection expectation.
        
        print(f"Testing whit Username")
        
        request = self.factory.get(f'/user?username={self.test_user_2.username}',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = UserView.as_view()
        response = view(request)
        response_data = response.data
        
        # ----------------------------------------------
        # Section 2.3.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.3.2: Result
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(SimpleUserSerializer(self.test_user_2).data,response_data, f"User's are different.")
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Expected User:\n{SimpleUserSerializer(self.test_user).data}\n")
            print(f"Response User:\n{response_data}")

        
        print_green("\nSuccess")
        self.success+= 1


    def test_patch_user(self):
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.

        print("\n")
        print(f"Running: {self.test_patch_user.__name__}")
        print("\n")

        self.total += 1
        view = UserView.as_view()       

        # ----------------------------------------------
        # Section 2: Validations
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")

        # ----------------------------------------------
        # Section 2.1: Update All Fields
        # ----------------------------------------------
        # This subsection updates all user fields simultaneously.
        
        print(f"Testing Update All Fields")

        update_data = {
            "name": "Updated Test User",
            "username": "updatedusername",
            "description": "This is an updated description.",
            "img_source":"test.png",
            "user_portion":5,
            "fmc_token":"xxxxx",
            #"birth_date": "2000-01-01T00:00:00Z",
            #"email": "updatedemail@example.com",
            "sex":User.SexType.MALE.value,
            "profile_type": User.ProfileType.PUBLIC.value,
            # Add other fields to update here
        }
        
        request = self.factory.patch(f'/user', update_data,content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        response = view(request)
        response_data = response.data
        
        # ----------------------------------------------
        # Section 2.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return

        # ----------------------------------------------
        # Section 2.1.2: Result
        # ----------------------------------------------
        # This sub-subsection focuses on result validation for updating all fields.
        
        self.test_user.refresh_from_db()
        for key, value in update_data.items():
            try:
                self.assertEqual(getattr(self.test_user, key), value)
            
            except AssertionError as e:
                print("\nFailed\n")
                self.error +=1
                print(f"AssertionError: {e}")
                print(f"Key: {key}")
                print(f"Expected: {getattr(self.test_user, key)}")
                print(f"Response: {value}")
                return


        
        # ----------------------------------------------
        # Section 2.2: Try update forbiden fields Fields
        # ----------------------------------------------
        # This subsection updates all user fields simultaneously.
        
        print(f"Testing Update All Forbiden Fields")

        update_data = {
            "id": 1,
            "last_login": "updatedusername",
            "birth_date": "2000-01-01T00:00:00Z",
            "img_source":"test.png",
            "email":"a@a.com",
            "is_active":False,
            "created_at":"2000-01-01T00:00:00Z",
            "age": 25,
            "is_admin":True,
            "user_type":User.UserType.ADMIN.value,
            "password":"teste",
            # Add other fields to update here
        }


        request = self.factory.patch(f'/user/{self.test_user.id}', update_data, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        response = view(request)
        response_data = response.data
        
        # ----------------------------------------------
        # Section 2.2.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        teste = 1
        # ----------------------------------------------
        # Section 2.3: Password 
        # ----------------------------------------------
        # This subsection updates all user fields simultaneously.
        
        print(f"Testing Update Password Field")
        
        # ----------------------------------------------
        # Section 2.3.1: Testing whit only password 
        # ----------------------------------------------
        # This subsection updates all user fields simultaneously.
        
        
        update_data = {
            "password":"teste",
        }

        request = self.factory.patch(f'/user/{self.test_user.id}', update_data, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        response = view(request)
        response_data = response.data
        
        # ----------------------------------------------
        # Section 2.3.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        
        # ----------------------------------------------
        # Section 2.3.2: Testing whit password and old_password
        # ----------------------------------------------
        # This subsection updates all user fields simultaneously.
        
        update_data = {
            "password":"TESTE",
            "old_password":self._test_user_password,
        }

        request = self.factory.patch(f'/user/{self.test_user.id}', update_data, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        response = view(request)
        response_data = response.data
        
        # ----------------------------------------------
        # Section 2.3.2.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        
        # ----------------------------------------------
        # Section 2.4: Biodata TODO
        # ----------------------------------------------
        # This subsection updates all user fields simultaneously.
        
        # ----------------------------------------------
        # Section 2.4.1: Update all biodata fields
        # ----------------------------------------------
        # This subsection updates all user fields simultaneously.
        
        print(f"Testing Update Biodata Fields")

        update_data = {
            "height": 180,
            "weight": 60,
            "activity_level": float(User.ActivityLevel.ACTIVE.value),
        }
        
        request = self.factory.patch(f'/user', update_data,content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        response = view(request)
        response_data = response.data
        
        # ----------------------------------------------
        # Section 2.4.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return

        # ----------------------------------------------
        # Section 2.4.1.2: Result
        # ----------------------------------------------
        # This sub-subsection focuses on result validation for updating all fields.
        
        self.test_user.refresh_from_db()
        for key, value in update_data.items():
            try:
                self.assertEqual(getattr(self.test_user, key), value)
            
            except AssertionError as e:
                print("\nFailed\n")
                self.error +=1
                print(f"AssertionError: {e}")
                print(f"Key: {key}")
                print(f"Expected: {getattr(self.test_user, key)}")
                print(f"Response: {value}")
                return

        # ----------------------------------------------
        # Section 2.4.2: Testing constraints
        # ----------------------------------------------
        # This subsection updates all user fields simultaneously.
        
        # ----------------------------------------------
        # Section 2.4.2.1: Upper limit
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        print(f"Testing Update Biodata Field's constraints. ( Upper Limit )")

        update_data = {
            "height": USER_MAX_HEIGHT+1,
            "weight": USER_MAX_WEIGHT+1,
            "activity_level": float(User.ActivityLevel.ACTIVE.value)+0.1,
        }
        
        request = self.factory.patch(f'/user', update_data,content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        response = view(request)
        response_data = response.data
        
        
        # ----------------------------------------------
        # Section 2.4.2.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return

        
        # ----------------------------------------------
        # Section 2.4.2: Lower limit
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        print(f"Testing Update Biodata Field's constraints. ( Lower Limit )")

        update_data = {
            "height": USER_MIN_HEIGHT-1,
            "weight": USER_MIN_HEIGHT-1,
        }
        
        request = self.factory.patch(f'/user', update_data,content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        response = view(request)
        response_data = response.data
        
        
        # ----------------------------------------------
        # Section 2.4.2.2.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests for updating all fields.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        
        print_green("\nSuccess")
        self.success +=1


    def test_delete_user(self):
            
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.

        print("\n")
        print(f"Running: {self.test_delete_user.__name__}")
        print("\n")
        
        # Get Auth Token
        
        auth_user_delete = login(factory = self.factory,
                            email = self.test_user_delete.email,
                            password = self._test_user_delete_password).data
        
        self.total += 1       
        
        
        # ----------------------------------------------
        # Section 2: Delete User
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")
        
        request = self.factory.delete('/user',HTTP_AUTHORIZATION=f'Bearer {auth_user_delete["access_token"]}')
        view = UserView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.1.1: Auth
        # ----------------------------------------------
        # Testing if user can re-login after delete
        
        auth_user_delete = login(factory = self.factory,
                            email = self.test_user_delete.email,
                            password = self._test_user_delete_password).data
        
        try:
            self.assertIn("error", auth_user_delete)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
    
        
        print_green("\nSuccess")
        self.success+= 1
        

class UsersToFollowViewTestCase(TestCase):
    
    def setUp(self):
        self.factory = RequestFactory()
        
        # General
        
        self.total = 0
        self.success = 0
        self.error = 0
        
        # Testing models
        
        self._test_user_password = 'password123' 
        
        self.test_user = User.objects.create_user(
            username='teste_user',
            email='teste_user@example.com',
            name='Test User',
            password=self._test_user_password,  
            birth_date=datetime(year=2000, month=1, day=1),  
        )
        
        self._test_user_2_password = 'password123' 
        
        self.test_user_2 = User.objects.create_user(
            username='teste_user_2',
            email='teste_user_2@example.com',
            name='Test User 2',
            password=self._test_user_2_password,  
            birth_date=datetime(year=2000, month=1, day=1),  
        )
        
        self._test_user_3_password = 'password123' 
        
        self.test_user_3 = User.objects.create_user(
            username='test_user_3',
            email='test_user_3@example.com',
            name='Test User 3',
            password=self._test_user_3_password, 
            birth_date=datetime(year=2000, month=1, day=1),
            profile_type = User.ProfileType.PUBLIC.value 
        )       
        
        # Get Auth Token
        
        self.auth = login(factory = self.factory,
                              email = self.test_user.email,
                              password = self._test_user_password).data


    def test_get_users_to_follow(self):
                
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.

        print("\n")
        print(f"Running: {self.test_get_users_to_follow.__name__}")
        print("\n")
        
        
        self.total += 1       
        
        
        # ----------------------------------------------
        # Section 2: Get Users To Follow
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")
        
        request = self.factory.get('/follow/find',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = UsersToFollowView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        
        # ----------------------------------------------
        # Section 2.1.2: Result
        # ----------------------------------------------
        # 
        
        
        # Test Metadata
        
        try:
            test_metadata(self,response_data)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # Test Result
        
        try:
            
            self.assertIn('result', response_data)
            self.assertIsInstance(response_data['result'], list)
            self.assertEqual(len(response_data['result']), 2)
            
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        expected_data = {'follower': False, 'request_sent': False, 'user': SimpleUserSerializer(self.test_user_2).data}
        
        try:
            self.assertEqual(expected_data,response_data['result'][0], f"User's are different.")
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Expected User:\n{expected_data}\n")
            print(f"Response User:\n{response_data['result'][0]}")
            return
    
        print_green("\nSuccess")
        self.success+= 1
        
    def test_create_follow(self):
                
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.

        print("\n")
        print(f"Running: {self.test_create_follow.__name__}")
        print("\n")
        
        
        self.total += 1       
        
        
        # ----------------------------------------------
        # Section 2: Create a follow link
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        
        # ----------------------------------------------
        # Section 2.1: Follow a public profile
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")
        
        request = self.factory.post(f'/follow?user_id={self.test_user_3.id}',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = FollowView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        
        # ----------------------------------------------
        # Section 2.1.2: Check if followers_c and follow_c have increased
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.test_user_3 = User.objects.get(id = self.test_user_3.id)
            self.assertEqual(self.test_user_3.followers_c, 1)
            
            self.test_user = User.objects.get(id = self.test_user.id)
            self.assertEqual(self.test_user.follows_c, 1)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        
        # ----------------------------------------------
        # Section 2.2: Follow a private profile
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")
        
        request = self.factory.post(f'/follow?user_id={self.test_user_2.id}',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = FollowView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.2.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.2.2: Result
        # ----------------------------------------------
        # 
    
        try:
            
            self.assertIn('message', response_data)
            
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        
        
        # ----------------------------------------------
        # Section 2.3: User follows himself
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")
        
        request = self.factory.post(f'/follow?user_id={self.test_user.id}',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = FollowView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.3.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.3.2: Result
        # ----------------------------------------------
        # 
    
        try:
            test_error(test_case = self,response_data = response_data, error_type = ERROR_TYPES.LOGICAL.value)
            
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Error Type Expected: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        
        # ----------------------------------------------
        # Section 2.4: User follows unexistent user
        # ----------------------------------------------
        # 
        
        print(f"\n")
        
        request = self.factory.post(f'/follow?user_id={5}',HTTP_AUTHORIZATION=f'Bearer {self.auth["access_token"]}')
        view = FollowView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.4.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.4.2: Result
        # ----------------------------------------------
        # 
    
        try:
            
            test_error(test_case = self,response_data = response_data, error_type = ERROR_TYPES.MISSING_MODEL.value)
            
        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Error Type Expected: {response.status_code}")
            print(f"Response: {response_data}")
            return
            
        
        print_green("\nSuccess")
        self.success+= 1
        
    def test_delete_follow_request(self):
            
        # ----------------------------------------------
        # Section 1: Init
        # ----------------------------------------------
        # Declare initial user data, and produce server response.

        print("\n")
        print(f"Running: {self.test_delete_follow_request.__name__}")
        print("\n")
        
        # Get Auth Token
        
        auth_user_2 = login(factory = self.factory,
                            email = self.test_user_2.email,
                            password = self._test_user_2_password).data
        
        self.total += 1       
        
        
        # ----------------------------------------------
        # Section 2: Delete Follow Request
        # ----------------------------------------------
        # This section contains tests to validate various aspects of the application.
        
        print(f"\n")
        
        request = self.factory.delete('/user',HTTP_AUTHORIZATION=f'Bearer {auth_user_delete["access_token"]}')
        view = UserView.as_view()
        response = view(request)
        response_data = response.data

        # ----------------------------------------------
        # Section 2.1.1: Connection
        # ----------------------------------------------
        # This sub-subsection focuses on connection tests with no arguments.
        
        try:
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
        
        # ----------------------------------------------
        # Section 2.1.1: Auth
        # ----------------------------------------------
        # Testing if user can re-login after delete
        
        auth_user_delete = login(factory = self.factory,
                            email = self.test_user_delete.email,
                            password = self._test_user_delete_password).data
        
        try:
            self.assertIn("error", auth_user_delete)

        except AssertionError as e:
            print_red("\nFailed\n")
            self.error +=1
            print(f"AssertionError: {e}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response_data}")
            return
    
        
        print_green("\nSuccess")
        self.success+= 1