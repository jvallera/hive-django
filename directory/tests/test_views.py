from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from registration.models import RegistrationProfile

from ..models import Organization
from ..management.commands.seeddata import create_user

class AccountProfileTests(TestCase):
    fixtures = ['wnyc.json']

    def setUp(self):
        super(AccountProfileTests, self).setUp()
        self.wnyc = Organization.objects.get(pk=1)
        create_user('non_member', password='lol')
        create_user('wnyc_member', email='member@wnyc.org', password='lol',
                    organization=self.wnyc)

    def test_edit_org_redirects_anonymous_users_to_login(self):
        c = Client()
        response = c.get('/accounts/profile/', follow=True)
        self.assertRedirects(response,
                             '/accounts/login/?next=/accounts/profile/')

    def test_profile_hides_membership_form_for_nonmembers(self):
        c = Client()
        c.login(username='wnyc_member', password='lol')
        response = c.get('/accounts/profile/')
        self.assertContains(response, 'Membership Information')

    def test_profile_shows_membership_form_for_members(self):
        c = Client()
        c.login(username='non_member', password='lol')
        response = c.get('/accounts/profile/')
        self.assertNotContains(response, 'Membership Information')

    def test_submitting_valid_form_changes_model(self):
        c = Client()
        c.login(username='non_member', password='lol')
        response = c.post('/accounts/profile/', {
            'user_profile-username': 'non_member',
            'user_profile-first_name': 'Non',
            'user_profile-last_name': 'Member'
        })
        self.assertRedirects(response, '/accounts/profile/')
        self.assertEqual(User.objects.get(username='non_member').first_name,
                         'Non')

class OrganizationProfileTests(TestCase):
    fixtures = ['wnyc.json', 'hivenyc.json']

    def setUp(self):
        super(OrganizationProfileTests, self).setUp()
        self.wnyc = Organization.objects.get(pk=1)
        self.hivenyc = Organization.objects.get(pk=2)
        create_user('non_member', password='lol')
        create_user('wnyc_member', email='member@wnyc.org', password='lol',
                    organization=self.wnyc)
        create_user('hivenyc_member', email='member@hivenyc.org',
                    password='lol', organization=self.hivenyc)

    def test_edit_org_redirects_anonymous_users_to_login(self):
        c = Client()
        response = c.get('/orgs/wnyc/edit/', follow=True)
        self.assertRedirects(response,
                             '/accounts/login/?next=/orgs/wnyc/edit/')

    def test_edit_org_gives_non_org_members_403(self):
        c = Client()
        c.login(username='hivenyc_member', password='lol')
        response = c.get('/orgs/wnyc/edit/')
        self.assertEqual(response.status_code, 403)

    def test_edit_org_gives_org_members_200(self):
        c = Client()
        c.login(username='wnyc_member', password='lol')
        response = c.get('/orgs/wnyc/edit/')
        self.assertEqual(response.status_code, 200)

class OrganizationTests(TestCase):
    fixtures = ['wnyc.json']

    def setUp(self):
        super(OrganizationTests, self).setUp()
        self.wnyc = Organization.objects.get(pk=1)

    def test_org_has_memberships(self):
        self.assertEqual(self.wnyc.memberships.count(), 0)
        create_user('foo', organization=self.wnyc)
        self.assertEqual(self.wnyc.memberships.count(), 1)

    def test_directory_listing_shows_orgs(self):
        c = Client()
        response = c.get('/')
        self.assertContains(response, 'Radio Rookies')

    def test_directory_listing_shows_emails_to_hive_members_only(self):
        create_user('non_member', password='lol')
        create_user('member', email='member@wnyc.org', password='lol',
                    organization=self.wnyc)

        c = Client()
        c.login(username='non_member', password='lol')
        response = c.get('/')
        self.assertNotContains(response, 'member@wnyc.org')

        c.login(username='member', password='lol')
        response = c.get('/')
        self.assertContains(response, 'member@wnyc.org')

    def activate_user(self, *args, **kwargs):
        user = create_user(is_active=False, *args, **kwargs)
        profile = RegistrationProfile.objects.create_profile(user)
        c = Client()
        response = c.get('/accounts/activate/%s/' % profile.activation_key)
        self.assertRedirects(response, '/accounts/activate/complete/')
        user = User.objects.get(username='somebody')
        self.assertEqual(user.is_active, True)
        return user

    def test_user_org_is_blank_on_activation_if_email_does_not_match(self):
        user = self.activate_user('somebody', password='lol',
                                  email='somebody@example.org')
        self.assertEqual(user.membership.organization, None)

    def test_user_org_is_assigned_on_activation_if_email_matches(self):
        user = self.activate_user('somebody', password='lol',
                                  email='somebody@wnyc.org')
        self.assertEqual(user.membership.organization.slug, 'wnyc')