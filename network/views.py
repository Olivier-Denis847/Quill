import json
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone, dateformat
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import User, Post
from django.contrib.auth.decorators import login_required


def index(request):
    return render(request, "network/index.html")

def following(request):
    return render(request, "network/following.html", {'user_id': request.user.id})

def profile(request, id):
    if request.method != 'GET':
        return

    user = User.objects.get(id = id)
    return render(request, 'network/profile.html', {
        'to_view' : user, 'followers' : user.followers.count(), 'following' : user.following.count(),
        'self' : request.user == user, 'follows' : (request.user in user.followers.all())})

@login_required
def add_follow(request, id):
    #Api route

    if request.method != 'PUT':
        return JsonResponse({'error' : 'Only PUT methods are supported'}, status = 400)
    
    data = json.loads(request.body)
    follows = data.get('follows')
    to_follow = User.objects.get(id = id)

    if follows == 'False':
        request.user.following.add(to_follow)
    elif follows == 'True':
        request.user.following.remove(to_follow)
    else:
        return JsonResponse({'error' : 'Bad request'}, status = 400)
    
    return JsonResponse({'message' : 'followed/unfollowed sucessfully'}, status = 201)

@login_required
def add_like(request):
    #Api route

    if request.method != 'PUT':
        return JsonResponse({'error' : 'Only PUT methods are supported'}, status = 400)
    
    data = json.loads(request.body)
    post = Post.objects.get(id = data.get('post_id'))
    liked = data.get('is_liked')

    if liked:
        post.likes.remove(request.user)
        return JsonResponse({'message' : 'removed like sucessfully'}, status = 201)
    post.likes.add(request.user)
    return JsonResponse({'message' : 'added like sucessfully'}, status = 201)

@login_required
def edit_post(request):
    #Api route 

    if request.method != 'PUT':
        return JsonResponse({'error' : 'Only PUT methods are supported'}, status = 400)
    
    data = json.loads(request.body)
    body = data.get('content')
    if len(body) == 0:
        return JsonResponse({'error' : 'Post body cannot be empty'}, status = 400)

    post = Post.objects.get(id = data.get('post_id'))
    if post.creator != request.user:
        return JsonResponse({'error' : 'You can only edit posts you own'}, status = 401)

    post.content = body
    post.save()
    return JsonResponse({'message' : 'post edited sucessfully'}, status = 201)

@login_required
def create_post(request):
    #Api route 

    if request.method != 'POST':
        return JsonResponse({'error' : 'Only POST methods are supported'}, status = 400)
    
    data = json.loads(request.body)
    if len(data['content']) == 0:
        return JsonResponse({'error' : 'Post body cannot be empty'}, status = 400)

    new_post = Post(content = data['content'], creator = request.user, posted = timezone.now())
    new_post.save()
    return JsonResponse({'message' : 'post created sucessfully'}, status = 201)

def list_posts(request):
    #Api route
    if request.method != 'GET':
        return JsonResponse({'error' : 'Only GET methods are supported'}, status = 400)
    user = request.GET.get('user', 'null')
    follows = request.GET.get('follows', 'false')
    page_num = request.GET.get('page', 1)

    if user == 'null':
        posts = Post.objects.all().order_by('-id')
    elif follows == 'false':
        sender = User.objects.get(id = user)
        posts = Post.objects.filter(creator = sender).all().order_by('-id')
    else:
        users = User.objects.get(id = user).following.all()
        posts = Post.objects.filter(creator__in=users).all().order_by('-id')
    
    paginator_obj = Paginator(posts, 10)
    try:
        page = paginator_obj.page(page_num)
    except PageNotAnInteger:
        page = paginator_obj.page(1)
    except EmptyPage:
        page = paginator_obj.page(paginator_obj.num_pages)

    items = []
    for post in page.object_list:
        formatted_date = dateformat.format(post.posted, 'Y-m-d H:i')
        summary = {
            'creator' : post.creator.username,
            'content' : post.content,
            'posted' : formatted_date,
            'likes' : post.likes.count(), 
            'creator_id' : post.creator.id,
            'post_id' : post.id,
            'is_liked' : post.likes.filter(id = request.user.id).exists(),
            'is_owner' : post.creator.id == request.user.id
        }
        items.append(summary)

    return JsonResponse({
        "current_page": page.number,
        "has_next": page.has_next(),
        "has_previous": page.has_previous(),
        "results": items}, safe=False)

def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "network/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "network/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "network/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, "placeholder", password)
            user.save()
        except IntegrityError:
            return render(request, "network/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "network/register.html")
