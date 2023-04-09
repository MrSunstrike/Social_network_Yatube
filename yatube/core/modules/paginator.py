from django.core.paginator import Paginator


def paginator(request, posts, amount):
    paginator = Paginator(posts, amount)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
