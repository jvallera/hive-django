import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, \
                        HttpResponseBadRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from .models import Organization, Membership, is_user_vouched_for, \
                    is_user_privileged
from .forms import ExpertiseFormSet, ExpertiseFormSetHelper, \
                   ContentChannelFormSet, ChannelFormSetHelper, \
                   MembershipForm, UserProfileForm, OrganizationForm

ORGS_PER_PAGE = 5

def is_request_privileged(request):
    return (request.user.is_authenticated() and
            is_user_privileged(request.user))

def validate_and_save_forms(*forms):
    forms = [form for form in forms if form is not None]
    for form in forms:
        if not form.is_valid(): return False
    for form in forms: form.save()
    return True

def home(request):
    all_orgs = Organization.objects.filter(is_active=True).order_by('name')
    paginator = Paginator(all_orgs, ORGS_PER_PAGE)

    page = request.GET.get('page')
    try:
        orgs = paginator.page(page)
    except PageNotAnInteger:
        orgs = paginator.page(1)
    except EmptyPage:
        orgs = paginator.page(paginator.num_pages)

    return render(request, 'directory/home.html', {
        'orgs': orgs,
        'show_privileged_info': is_request_privileged(request)
    })

def find_json(request):
    query = request.GET.get('query')
    results = []
    if not query:
        return HttpResponseBadRequest('query must be non-empty')

    orgs = Organization.objects.filter(name__icontains=query,
                                       is_active=True)
    results.extend([
        {'value': org.name, 'url': org.get_absolute_url()}
        for org in orgs
    ])

    if is_request_privileged(request):
        memberships = Membership.objects.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query),
            is_listed=True,
            user__is_active=True
        )
        results.extend([
            {'value': membership.user.get_full_name(),
             'url': membership.get_absolute_url()}
            for membership in memberships
        ])

    return HttpResponse(json.dumps(results), content_type='application/json')

def organization_detail(request, organization_slug):
    org = get_object_or_404(Organization, slug=organization_slug,
                            is_active=True)
    return render(request, 'directory/organization_detail.html', {
        'org': org,
        'show_privileged_info': is_request_privileged(request)
    })

@login_required
def organization_edit(request, organization_slug):
    org = get_object_or_404(Organization, slug=organization_slug,
                            is_active=True)
    user = request.user
    if not (user.is_superuser or is_user_vouched_for(user, org)):
        return HttpResponseForbidden('Permission denied.')
    if request.method == 'POST':
        form = OrganizationForm(request.POST, instance=org, prefix='org')
        channel_formset = ContentChannelFormSet(request.POST, instance=org,
                                                prefix='chan')
        if form.is_valid() and channel_formset.is_valid():
            form.save()
            channel_formset.save()
            messages.success(request,
                             'The organization profile has been updated.')
            return redirect('organization_detail', org.slug)
        else:
            messages.error(request, 'Your submission had some problems.')
    else:
        form = OrganizationForm(instance=org, prefix='org')
        channel_formset = ContentChannelFormSet(instance=org, prefix='chan')
    channel_formset_helper = ChannelFormSetHelper()
    return render(request, 'directory/organization_edit.html', {
        'org': org,
        'form': form,
        'channel_formset': channel_formset,
        'channel_formset_helper': channel_formset_helper
    })

@user_passes_test(is_user_privileged)
def user_detail(request, username):
    membership = get_object_or_404(Membership, user__username=username,
                                   user__is_active=True)
    return render(request, 'directory/user_detail.html', {
        'membership': membership
    })

@login_required
def user_edit(request):
    user = request.user
    membership_form = None
    data = None

    if request.method == 'POST': data = request.POST
    if is_user_vouched_for(user):
        membership_form = MembershipForm(data=data,
                                         instance=user.membership,
                                         prefix='membership')
    user_profile_form = UserProfileForm(data=data,
                                        instance=user,
                                        prefix='user_profile')
    expertise_formset = ExpertiseFormSet(data=data, instance=user,
                                         prefix='expertise')
    if request.method == 'POST':
        if validate_and_save_forms(user_profile_form, membership_form,
                                   expertise_formset):
            messages.success(request, 'Your profile has been updated.')
            return redirect('user_edit')
        else:
            messages.error(request, 'Your submission had some problems.')

    return render(request, 'directory/user_edit.html', {
        'membership_form': membership_form,
        'user_profile_form': user_profile_form,
        'expertise_formset': expertise_formset,
        'expertise_formset_helper': ExpertiseFormSetHelper()
    })
