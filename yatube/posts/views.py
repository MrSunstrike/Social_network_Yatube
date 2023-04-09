from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.modules.paginator import paginator

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User

POSTS_AMOUNT = 10


def index(request):
    template = 'posts/index.html'
    posts = Post.objects.all()
    context = {'page_obj': paginator(request, posts, POSTS_AMOUNT)}
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    template = 'posts/group_list.html'
    posts = group.posts.all()
    context = {
        'group': group,
        'page_obj': paginator(request, posts, POSTS_AMOUNT)
    }
    return render(request, template, context)


def profile(request, username):
    author = User.objects.get(username=username)
    posts = Post.objects.filter(author=author)
    relation = None
    if request.user.is_authenticated:
        relation = Follow.objects.filter(user=request.user, author=author)
    following = True if relation else False
    context = {
        'author': author,
        'page_obj': paginator(request, posts, POSTS_AMOUNT),
        'following': following
    }

    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = Post.objects.get(pk=post_id)
    form = CommentForm()
    comments = post.comments.all()
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    user = request.user
    template = 'posts/create_edit_post.html'
    form = PostForm()
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            text = form.cleaned_data['text']
            group = form.cleaned_data['group']
            image = form.cleaned_data['image']
            post = Post(text=text, group=group, author=user, image=image)
            post.save()
            return redirect('posts:profile', user.username)
        return render(request, template, {'form': form})

    return render(request, template, {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    template = 'posts/create_edit_post.html'
    is_edit = True
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(request.POST or None, instance=post)
    if request.method == 'POST':
        if form.is_valid():
            post.text = form.cleaned_data['text']
            post.group = form.cleaned_data['group']
            post.image = request.FILES.get('image', post.image)
            post.save()
            return redirect('posts:post_detail', post.pk)
        return render(request, template, {
            'form': form, 'is_edit': is_edit, 'post': post
        })
    return render(request, template, {
        'form': form, 'is_edit': is_edit, 'post': post
    })


@login_required
def add_comment(request, post_id):
    post = Post.objects.get(id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    all_following = Follow.objects.filter(user=request.user)
    author_list = all_following.values_list('author', flat=True)
    posts = Post.objects.filter(author__in=author_list)
    context = {'page_obj': paginator(request, posts, POSTS_AMOUNT)}
    template = 'posts/follow.html'
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = User.objects.get(username=username)
    check_relation = Follow.objects.filter(user=user, author=author)
    if not check_relation:
        Follow.objects.create(user=user, author=author)
        return redirect('posts:profile', username=author)
    else:
        return redirect('posts:profile', username=author)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = User.objects.get(username=username)
    check_relation = Follow.objects.filter(user=user, author=author)
    if check_relation:
        following = Follow.objects.get(user=user, author=author)
        following.delete()
        return redirect('posts:profile', username=author)
    else:
        return redirect('posts:profile', username=author)
