from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.modules.paginator import paginator

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User

POSTS_AMOUNT = 10


def index(request):
    """
    Рендерит главную страницу со списком всех постов, разбитым на страницы.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.

    Возвращает:
        HttpResponse: Ответ, содержащий отрендеренный шаблон index.html и
        контекст, содержащий список всех постов, разбитый на страницы.
    """
    template = 'posts/index.html'
    posts = Post.objects.all()
    context = {'page_obj': paginator(request, posts, POSTS_AMOUNT)}
    return render(request, template, context)


def group_posts(request, slug):
    """
    Рендерит страницу со списком всех постов в заданной группе, разбитым на
    страницы.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        slug (str): Slug-значение группы, для которой нужно отобразить список
        постов.

    Возвращает:
        HttpResponse: Ответ, содержащий отрендеренный шаблон group_list.html и
        контекст, содержащий группу и список всех постов в этой группе,
        разбитый на страницы.
    """
    group = get_object_or_404(Group, slug=slug)
    template = 'posts/group_list.html'
    posts = group.posts.all()
    context = {
        'group': group,
        'page_obj': paginator(request, posts, POSTS_AMOUNT)
    }
    return render(request, template, context)


def profile(request, username):
    """
    Рендерит страницу профиля пользователя, включая список всех его постов,
    разбитый на страницы.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        username (str): Имя пользователя, чей профиль нужно отобразить.

    Возвращает:
        HttpResponse: Ответ, содержащий отрендеренный шаблон profile.html и
        контекст, содержащий профиль пользователя, список всех его постов и
        информацию о том, подписан ли текущий пользователь на этого
        пользователя.
    """
    author = User.objects.get(username=username)
    posts = Post.objects.filter(author=author)
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user, author=author
    )
    context = {
        'author': author,
        'page_obj': paginator(request, posts, POSTS_AMOUNT),
        'following': following
    }

    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """
    Рендерит страницу с подробной информацией о посте, включая список всех
    комментариев.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        post_id (int): Идентификатор поста, чью детальную информацию нужно
        отобразить.

    Возвращает:
        HttpResponse: Ответ, содержащий отрендеренный шаблон post_detail.html
        и контекст, содержащий информацию о посте и список всех комментариев
        к этому посту.
    """
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
    """
    Рендерит страницу создания нового поста и сохраняет новый пост в базе
    данных.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.

    Возвращает:
        HttpResponse: Ответ, содержащий отрендеренный шаблон
        create_edit_post.html и контекст, содержащий форму создания нового
        поста. Если форма заполнена неверно, возвращается та же страница с
        формой и ошибками. После успешного создания поста, пользователь
        перенаправляется на свой профиль.
    """
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


@login_required
def post_edit(request, post_id):
    """
    Рендерит страницу редактирования поста и обновляет его в базе данных.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        post_id (int): Идентификатор поста, который нужно отредактировать.

    Возвращает:
        HttpResponse: Ответ, содержащий отрендеренный шаблон
        create_edit_post.html и контекст, содержащий форму редактирования поста
        и соответствующий пост. Если форма заполнена неверно, возвращается та
        же страница с формой и ошибками. После успешного редактирования поста,
        пользователь перенаправляется на страницу с деталями измененного поста.
        Если пользователь не является автором поста, он перенаправляется на
        страницу с деталями поста.
    """
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
def post_remove(request, post_id):
    """
    Удаляет пост из базы данных.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        post_id (int): Идентификатор поста, который нужно удалить.

    Возвращает:
        HttpResponse: Ответ, который перенаправляет пользователя на страницу,
        откуда была отправлена форма удаления поста. Если пользователь не
        является автором поста, он также перенаправляется на эту же страницу.
    """
    current_url = request.META.get('HTTP_REFERER')
    # Этой конструкцией я пытался изящно решить проблемы, связанные с кэшем
    # Но ок, пусть пользователя кидает на 404
    post = get_object_or_404(Post, pk=post_id)
    if request.user == post.author:
        post.delete()
    return redirect(current_url)


@login_required
def add_comment(request, post_id):
    """
    Добавляет новый комментарий к посту в базе данных.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        post_id (int): Идентификатор поста, к которому нужно добавить
        комментарий.

    Возвращает:
        HttpResponse: Ответ, который перенаправляет пользователя на страницу с
        деталями поста, к которому был добавлен комментарий.
    """
    post = Post.objects.get(id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def remove_comment(request, comment_id):
    """
    Удаляет комментарий из базы данных.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        comment_id (int): Идентификатор комментария, который нужно удалить.

    Возвращает:
        HttpResponse: Ответ, который перенаправляет пользователя на страницу,
        откуда была отправлена форма удаления комментария. Если пользователь не
        является автором комментария, он также перенаправляется на эту же
        страницу.
    """
    current_url = request.META.get('HTTP_REFERER')
    comment = get_object_or_404(Comment, pk=comment_id)
    if request.user == comment.author:
        comment.delete()
    return redirect(current_url)


@login_required
def follow_index(request):
    """
    Рендерит страницу с постами пользователей, на которых подписан текущий
    пользователь.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.

    Возвращает:
        HttpResponse: Ответ, содержащий отрендеренный шаблон follow.html и
        контекст, содержащий список постов пользователей, на которых подписан
        текущий пользователь.
    """
    all_following = Follow.objects.filter(user=request.user)
    author_list = all_following.values_list('author', flat=True)
    posts = Post.objects.filter(author__in=author_list)
    is_following = True if len(posts) > 0 else False
    context = {'page_obj': paginator(request, posts, POSTS_AMOUNT),
               'is_following': is_following}
    template = 'posts/follow.html'
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    """
    Создает отношение подписки между текущим пользователем и другим
    пользователем.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        username (str): Имя пользователя, на которого нужно подписаться.

    Возвращает:
        HttpResponse: Ответ, который перенаправляет пользователя на страницу
        профиля пользователя, на которого он подписался.
    """
    user = request.user
    author = User.objects.get(username=username)
    if user != author:
        check_relation = Follow.objects.filter(user=user, author=author)
        if not check_relation:
            Follow.objects.create(user=user, author=author)
    # Спасибо, везде почистил лишние else и return
    return redirect('posts:profile', username=author)


@login_required
def profile_unfollow(request, username):
    """
    Удаляет отношение подписки между текущим пользователем и другим
    пользователем.

    Аргументы:
        request (HttpRequest): Объект запроса, переданный Django.
        username (str): Имя пользователя, от которого нужно отписаться.

    Возвращает:
        HttpResponse: Ответ, который перенаправляет пользователя на страницу
        профиля пользователя, от которого он отписался.
    """
    user = request.user
    author = User.objects.get(username=username)
    check_relation = Follow.objects.filter(user=user, author=author)
    if check_relation:
        following = Follow.objects.get(user=user, author=author)
        following.delete()
    return redirect('posts:profile', username=author)
