from django.shortcuts import render, redirect
from .forms import signup_form, login_form, post_form, bookingform
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseNotAllowed
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.contrib import messages
from .models import Newuser, post
from json import dumps
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
import json
import os
import datetime
from datetime import timedelta
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
import iso8601
import google_apis_oauth
from oauth2client.client import OAuth2WebServerFlow
import httplib2
from django.core.files import File

 

# Create your views here.

REDIRECT_URI = 'http://127.0.0.1:8000/google_oauth/callback/'
CLIENT_ID = '167022070572-tlo92orjtfavmuas01nnvt0h9cteth6d.apps.googleusercontent.com'
CLIENT_SECRET = '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'
SCOPES = ['https://www.googleapis.com/auth/calendar']

JSON_FILEPATH = 'client_secret.json'

def RedirectOauthView(request):
    oauth_url = google_apis_oauth.get_authorization_url(
        JSON_FILEPATH, SCOPES, REDIRECT_URI)
    return(oauth_url)
   

def callbackView(request):
    credentials = google_apis_oauth.get_crendentials_from_callback(
            request,
            JSON_FILEPATH,
            SCOPES,
            REDIRECT_URI
        )
    uname=request.session['username']
    stringified_token = google_apis_oauth.stringify_credentials(credentials)
    olp={uname:stringified_token}
    d=[]
    if os.path.getsize('doctor_id.json') > 0:
        f = open('doctor_id.json', 'r')
        # wf=open('doctor_id.json', 'w')
        if f.mode == 'r':
            contents =f.read() 
            cont=(json.loads(contents))
            for i in cont:  
                d.append(i) 
            d.append(json.dumps(olp)) 
        f.close
        wf=open('doctor_id.json', 'w')
        clientfile = File(wf)
        clientfile.write(json.dumps(d))
        clientfile.close
        wf.close
    else:
        uf=open('doctor_id.json', 'w')
        clientfile = File(uf)
        d.append(json.dumps(olp))
        clientfile.write(json.dumps(d))
        clientfile.close
        uf.close

    return HttpResponseRedirect('/')

   



def onlanding(request):
    if request.method == "POST":
        fm=login_form(request=request, data=request.POST)
        if fm.is_valid():
            uname=fm.cleaned_data['username']
            pword=fm.cleaned_data['password']
            usr= authenticate(username=uname, password=pword)
            if usr is not None:
                login(request, usr)
                group = None
                if usr.groups.exists():
                    group = usr.groups.all()[0].name
                    if group == 'Doctor':
                        return HttpResponseRedirect('/dashdoctor/')
                    if group == 'Patient':
                        return HttpResponseRedirect('/dashpatient/')
        else:
            messages.error(request, "Invalid Credentials!!!")
            return HttpResponseRedirect('/')
    else:
        fm= login_form()
    return render(request, 'login.html', {'form': fm})
   


def signup(request):
    if request.method == "POST":
        fm=signup_form(request.POST, request.FILES)
        if fm.is_valid():
            user = fm.save()
            request.session['username'] = user.username
            group = Group.objects.get(name=request.POST.get('groups'))
            user.groups.add(group)
            confrim=RedirectOauthView(request)
            messages.success(request, "Account created successfully!!!")
            return HttpResponseRedirect(confrim)

    else:
        fm= signup_form()
    return render(request, 'signup.html', {'form':fm})

    
def dashboard_doctor(request):
    if request.method == "POST":
        form = post_form(request.POST, request.FILES)
        if form.is_valid():
            pt= form.save()
            data={
                "id":pt.id,
                "title":pt.title,
                "postimg":pt.postimg.url,
                "categories":pt.categories,
                "summary":pt.summary,
                "content":pt.content,
                "is_draft":pt.is_draft,
            }
            return JsonResponse({"postdata":data})
        else:
            return JsonResponse({"msg":"Invalid data"})
    else:
        fm=post_form()
        postMH=post.objects.filter(categories='MENTAL HEALTH')
        postHD=post.objects.filter(categories='HEART DISEASE')
        postC19=post.objects.filter(categories='COVID19')
        postIZ=post.objects.filter(categories='IMMUNIZATION')
        context={
           'form':fm,
           'postMH':postMH,
           'postHD':postHD,
           'postC19':postC19,
           'postIZ':postIZ,
           'author':request.user.username,

        }
        return render(request, 'dashdoctor.html', context)

@csrf_exempt
def dashboard_patient(request):
    if 'confm' in request.POST:
        form=bookingform(request.POST)
        if form.is_valid():
            un=form.cleaned_data['uname']
            dn=form.cleaned_data['dname']
            rs=form.cleaned_data['required_speciality']
            doa=form.cleaned_data['date_of_appointment']
            toa=form.cleaned_data['time_of_appointment']
            cdt = datetime.datetime.combine(doa, toa)
            pname=request.user.username
            evnt=create_event(pname,un, rs, cdt)
            dt=iso8601.parse_date(evnt['start']['dateTime'])
            enddt=iso8601.parse_date(evnt['end']['dateTime'])
            dname=dn
            date=dt.date()
            time=dt.time()
            endtime=enddt.time()
            context={
                'dname':dname,
                'date':date,
                'time':time,
                'endtime':endtime,
            }

        return render(request, 'appointmentdetails.html', context)

    if request.method=="POST":
        fm=bookingform()
        template = render_to_string('booking.html', {'fm':fm})
        pstobj=post.objects.all()
        Usr = get_user_model()
        userogj = Usr.object.filter(groups__name='Doctor')
        usr_data=[]
        blog_data=[]
        for pst in pstobj:
            item={
                "id":pst.id,
                "title":pst.title,
                "postimg":pst.postimg.url,
                "categories":pst.categories,
                "summary":pst.summary,
                "content":pst.content,
                "is_draft":pst.is_draft,
            }
            blog_data.append(item)

        for usr in userogj:
            item={
                "id":usr.id,
                "username":usr.username,
                "fname":usr.first_name,
                "lname":usr.last_name,
                "profilepic":usr.profilepic.url,
            }
            usr_data.append(item)


        context={
            "postdata":blog_data,
            "usrdata":usr_data,
            "appointform":template,
        }

        return JsonResponse({"alldata":context})
    else:
        defaultdata=post.objects.filter(categories="MENTAL HEALTH", is_draft=False)
    return render(request, 'dashpatient.html', {'dt':defaultdata})

def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

def postview(request, pk):
    postobj=post.objects.get(id=pk)
    return render(request, 'viewpost.html', {'pt':postobj})



def build_service(un):
    # service_account_email = "task3-615@task3-343409.iam.gserviceaccount.com "
    f = open('doctor_id.json', 'r')
    if f.mode == 'r':
       contents =f.read()
       tokens=json.loads(contents)
       for i in tokens:
           u=json.loads(i)
           if un in u.keys():
                cr=u

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    credentials=cr[un]
    creds, refreshed = google_apis_oauth.load_credentials(credentials)
    service = build("calendar", "v3", credentials=creds)
    return service

def create_event(pname,un, rs, cdt):
    service = build_service(un)
    start_datetime = cdt.isoformat()+ "+05:30"
    event = (
        service.events()
        .insert(
            calendarId="primary",
            body={
                "summary": pname,
                "description": rs,
                "start": {"dateTime": start_datetime},
                "end": {
                    "dateTime": (cdt + timedelta(minutes=45)).isoformat()+ "+05:30"
                },
            },
        )
        .execute()
    )
    return (event)

@csrf_exempt
def confrm(request):
    if request.method == "POST":
        usrname = json.loads(request.body)
        fm=bookingform(initial={'dname':usrname['dt'], 'uname':usrname['usrnm']})
        template = render_to_string('booking.html', {'fm':fm, 'dname':usrname['dt'],'uname':usrname['usrnm'] })
    return JsonResponse({"appointfm":template})







