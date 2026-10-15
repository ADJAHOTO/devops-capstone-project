"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app
from service import talisman

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"

HTTPS_ENVIRON = {'wsgi.url_scheme': 'https'}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    ######################################################################
    #  R E A D   T E S T   C A S E S
    ######################################################################

    def test_get_account(self):
        """It should Read a single Account"""
        # Create an account
        account = self._create_accounts(1)[0]

        # Read the account
        resp = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.get_json()
        self.assertEqual(data["name"], account.name)
        self.assertEqual(data["email"], account.email)
        self.assertEqual(data["address"], account.address)
        self.assertEqual(data["phone_number"], account.phone_number)

    def test_get_account_not_found(self):
        """It should not Read an Account that doesn't exist"""
        resp = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    ######################################################################
    #  L I S T   T E S T   C A S E S
    ######################################################################

    def test_list_all_accounts(self):
        """It should List all Accounts in the database"""
        accounts = self._create_accounts(5)
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)
        # Check that the accounts match
        account_ids = [account.id for account in accounts]
        for account in data:
            self.assertIn(account["id"], account_ids)

    def test_list_empty_accounts(self):
        """It should return an empty list when there are no Accounts"""
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data, [])

    ######################################################################
    #  U P D A T E   T E S T   C A S E S
    ######################################################################

    def test_update_account(self):
        """It should Update an existing Account"""
        # Create an account
        account = self._create_accounts(1)[0]

        # Update it
        new_data = {
            "name": "Updated Name",
            "email": account.email,
            "address": account.address,
            "phone_number": account.phone_number,
            "date_joined": str(account.date_joined),
        }
        resp = self.client.put(
            f"{BASE_URL}/{account.id}",
            json=new_data,
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Check the data was updated
        updated_account = resp.get_json()
        self.assertEqual(updated_account["name"], "Updated Name")

    def test_update_account_not_found(self):
        """It should not Update an Account that doesn't exist"""
        new_data = {"name": "Nobody", "email": "nobody@nowhere.com"}
        resp = self.client.put(
            f"{BASE_URL}/0",
            json=new_data,
            content_type="application/json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    ######################################################################
    #  D E L E T E   T E S T   C A S E S
    ######################################################################

    def test_delete_account(self):
        """It should Delete an Account"""
        # Create an account
        account = self._create_accounts(1)[0]

        # Delete it
        resp = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        # Verify it's gone
        resp = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_account_not_found(self):
        """It should not Delete an Account that doesn't exist"""
        resp = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    ######################################################################
    #  S E C U R I T Y   T E S T   C A S E S
    ######################################################################

    def test_security_headers(self):
        """It should return security headers"""
        response = self.client.get("/", environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = {
            'X-Frame-Options': 'SAMEORIGIN',
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'self'; object-src 'none'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        for key, value in headers.items():
            self.assertEqual(response.headers.get(key), value)

    def test_cors_headers(self):
        """It should return CORS headers"""
        response = self.client.get("/", environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), '*')
