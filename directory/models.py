from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from registration.signals import user_activated

from .twitter import TwitterNameField
from .phonenumber import PhoneNumberField

def is_user_vouched_for(user, organization=None):
    '''
    Returns whether the given user belongs to a Hive-affiliated
    organization. If an organization is supplied, returns
    whether the user belongs to that organization specifically.
    '''

    if not (user.is_active and user.membership.organization
            and user.membership.organization.is_active):
        return False
    if organization is None: return True
    return organization == user.membership.organization

def is_user_privileged(user):
    '''
    Returns whether the given user can view personally identifiable
    information, phone numbers, and so forth.
    '''

    return is_user_vouched_for(user) or (user.is_active and user.is_staff)

class Organization(models.Model):
    '''
    Represents a Hive organization.
    '''

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(
        help_text="The full name of the organization.",
        max_length=100
    )
    slug = models.SlugField(
        help_text="A short identifier for the organization, used in "
                  "URLs and such. Only letters, numbers, underscores, and "
                  "hyphens are allowed.",
        unique=True
    )
    website = models.URLField(
        help_text="The URL of the organization's primary website."
    )
    email_domain = models.CharField(
        help_text="The domain which members of this organization have "
                  "email addresses at.",
        blank=True,
        max_length=50
    )
    address = models.TextField(
        help_text="The full address of the organization's main office.",
        blank=True,
    )
    twitter_name = TwitterNameField(
        help_text="The twitter account for the organization.",
        blank=True,
    )
    hive_member_since = models.DateField(
        help_text="The date the organization joined the Hive network. "
                  "Only the month and year will be used.",
        null=True,
        blank=True
    )
    mission = models.TextField(
        help_text="The organization's mission and philosophy. Markdown "
                  "and basic HTML tags are allowed.",
        blank=True,
    )
    min_youth_audience_age = models.SmallIntegerField(
        help_text="Minimum age of youth, in years, that the organization's "
                  "programs target.",
        validators=[MinValueValidator(0)],
        default=0
    )
    max_youth_audience_age = models.SmallIntegerField(
        help_text="Maximum age of youth, in years, that the organization's "
                  "programs target.",
        validators=[MinValueValidator(0)],
        default=18
    )
    is_active = models.BooleanField(
        help_text="Designates whether this organization should be treated "
                  "as active. Unselect this instead of deleting "
                  "organizations.",
        default=True
    )

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('organization_detail', args=(str(self.slug),))

    def membership_directory(self):
        return self.memberships.filter(
            is_listed=True,
            user__is_active=True
        ).order_by('user__last_name')

    def clean(self):
        if self.max_youth_audience_age < self.min_youth_audience_age:
            raise ValidationError("Minimum youth audience age may not "
                                  "be greater than maximum youth audience "
                                  "age.")

class Expertise(models.Model):
    '''
    Represents an expertise that a user has.
    '''

    CATEGORY_CHOICES = (
        ('youth', 'Youth'),
        ('partnerships', 'Collaboration and Partnerships'),
        ('rfp', 'RFP'),
        ('leveragingresources', 'Leveraging Resources'),
        ('volunteers', 'Mentors and Volunteers'),
        ('sharingoutcomes', 'Sharing Outcomes'),
        ('events', 'Activities and Events'),
        ('programdesign', 'Program Design and Facilitation'),
        ('badges', 'Badges'),
        ('innovation', 'Innovation Design Strategies'),
        ('leveraginghive', 'Leveraging Hive'),
        ('curriculum', 'Curriculum Development'),
        ('assessment', 'Assessment and Evaluative Approaches'),
        ('technology', 'Technological Solutions and Possibilities'),
        ('other', 'Other'),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    category = models.CharField(
        help_text="The type of the expertise",
        choices=CATEGORY_CHOICES,
        max_length=25,
    )

    details = models.CharField(
        max_length=255,
        blank=True,
        help_text="Details about the expertise",
    )

    user = models.ForeignKey(
        User,
        related_name='skills'
    )

class ContentChannel(models.Model):
    '''
    Represents a content channel for a Hive organization.
    '''

    FA_ICONS = {
        'facebook': 'fa-facebook-square',
        'youtube': 'fa-youtube-square',
        'vimeo': 'fa-vimeo-square',
        'flickr': 'fa-flickr',
        'tumblr': 'fa-tumblr-square',
        'pinterest': 'fa-pinterest-square',
        'github': 'fa-github-square',
        'instagram': 'fa-instagram',
    }

    CATEGORY_CHOICES = (
        ('facebook', 'Facebook'),
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo'),
        ('flickr', 'Flickr'),
        ('tumblr', 'Tumblr'),
        ('pinterest', 'Pinterest'),
        ('github', 'GitHub'),
        ('instagram', 'Instagram'),
        ('other', 'Other'),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    category = models.CharField(
        help_text="The type of the content channel",
        choices=CATEGORY_CHOICES,
        max_length=15,
    )

    name = models.CharField(
        help_text="The name of the content channel.",
        max_length=100,
        blank=True
    )

    url = models.URLField(
        help_text="The URL of the content channel.",
    )

    organization = models.ForeignKey(
        Organization,
        related_name='content_channels'
    )

    @property
    def fa_icon(self):
        '''
        The Font Awesome icon name for the channel.
        '''

        return self.FA_ICONS.get(self.category, '')

    @property
    def display_name(self):
        '''
        The full name of the content channel, for display to users.
        '''

        for name, display_name in self.CATEGORY_CHOICES:
            if name == self.category:
                break

        if self.category == 'other' and self.name:
            return self.name

        return display_name

class Membership(models.Model):
    '''
    Represents a person who is a member of an organization.
    '''

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User)
    organization = models.ForeignKey(Organization, blank=True, null=True,
                                     related_name='memberships')
    title = models.CharField(
        help_text="The person's title at their organization.",
        max_length=100,
        blank=True
    )
    twitter_name = TwitterNameField(
        help_text="The twitter account for the person.",
        blank=True,
    )
    phone_number = PhoneNumberField(
        help_text="The person's phone number.",
        blank=True
    )
    receives_minigroup_digest = models.BooleanField(
        default=False,
        help_text="Whether the person is sent a daily digest of Minigroup "
                  "activity."
    )
    is_listed = models.BooleanField(
        default=True,
        help_text="Whether the person is listed under their organization in "
                  "the Hive directory."
    )

    def get_absolute_url(self):
        return reverse('user_detail', args=(str(self.user.username),))

    def __unicode__(self):
        return u'Membership for %s' % self.user.username

class ImportedUserInfo(models.Model):
    '''
    Represents book-keeping about users who were imported from another
    data source, e.g. a Google Spreadsheet.
    '''

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User)
    was_sent_email = models.BooleanField(
        default=False,
        help_text="Whether the imported user has been sent an email "
                  "informing them of their new account."
    )

    def __unicode__(self):
        return u'Imported user info for %s' % self.user.username

@receiver(post_save, sender=User)
def create_membership_for_user(sender, raw, instance, **kwargs):
    if raw: return
    if not len(Membership.objects.filter(user=instance)):
        membership = Membership(user=instance)
        membership.save()

@receiver(user_activated)
def auto_register_user_with_organization(sender, user, request, **kwargs):
    if not (user.email and '@' in user.email): return
    if user.membership.organization: return
    domain_name = user.email.split('@')[1]
    orgs = Organization.objects.filter(email_domain=domain_name)
    if orgs.count() != 1: return
    org = orgs[0]
    user.membership.organization = org
    user.membership.save()
