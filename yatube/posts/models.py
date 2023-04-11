from django.contrib.auth import get_user_model
from django.db import models

from core.models import CreatedModel

User = get_user_model()


class Group(models.Model):
    """
    Модель, описывающая группу постов.

    Атрибуты:
        title (CharField): Заголовок группы, который не должен превышать
        200 символов.
        slug (SlugField): Уникальное поле, которое служит идентификатором
        группы в URL-адресах.
        description (TextField): Описание группы, которое может содержать
        множество символов.

    Метаданные:
        verbose_name (str): Человекочитаемое название модели в единственном
        числе.
        verbose_name_plural (str): Человекочитаемое название модели во
        множественном числе.

    Методы:
        __str__(): Возвращает заголовок группы в виде строки.

    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

    def __str__(self):
        return self.title


class Post(CreatedModel):
    """
    Модель, описывающая посты в блоге.

    Атрибуты:
        text (TextField): Текст поста, который может содержать множество
        символов.
        author (ForeignKey): Ссылка на пользователя, который написал пост.
        group (ForeignKey): Ссылка на группу, к которой относится пост. Может
        быть пустым.
        image (ImageField): Изображение поста, которое может быть пустым.

    Метаданные:
        ordering (list): Список полей, по которым будут сортироваться объекты
        модели.
        verbose_name (str): Человекочитаемое название модели в единственном
        числе.
        verbose_name_plural (str): Человекочитаемое название модели во
        множественном числе.

    Методы:
        __str__(): Возвращает первые 15 символов текста поста в виде строки.

    """
    text = models.TextField(
        verbose_name='Текст поста',
        help_text='Введите текст поста'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        related_name='posts',
        blank=True,
        null=True,
        verbose_name='Группа',
        help_text='Группа, к которой будет относиться пост'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.text[:15]


class Comment(CreatedModel):
    """
    Модель, описывающая комментарии к постам в блоге.

    Атрибуты:
        post (ForeignKey): Ссылка на пост, к которому относится комментарий.
        author (ForeignKey): Ссылка на пользователя, который написал
        комментарий.
        text (TextField): Текст комментария, который может содержать множество
        символов.

    Метаданные:
        ordering (list): Список полей, по которым будут сортироваться объекты
        модели.
        verbose_name (str): Человекочитаемое название модели в единственном
        числе.
        verbose_name_plural (str): Человекочитаемое название модели во
        множественном числе.

    Методы:
        __str__(): Возвращает первые 15 символов текста комментария в виде
        строки.

    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    text = models.TextField(
        verbose_name='Текст комментария',
        help_text='Введите текст комментария'
    )

    class Meta:
        ordering = ['-created']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return self.text[:15]


class Follow(models.Model):
    """
    Модель, описывающая комментарии к постам в блоге.

    Атрибуты:
        post (ForeignKey): Ссылка на пост, к которому относится комментарий.
        author (ForeignKey): Ссылка на пользователя, который написал
        комментарий.
        text (TextField): Текст комментария, который может содержать множество
        символов.

    Метаданные:
        ordering (list): Список полей, по которым будут сортироваться объекты
        модели.
        verbose_name (str): Человекочитаемое название модели в единственном
        числе.
        verbose_name_plural (str): Человекочитаемое название модели во
        множественном числе.

    Методы:
        __str__(): Возвращает первые 15 символов текста комментария в виде
        строки.

    """
    user = models.ForeignKey(
        User,
        related_name='follower',
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        User,
        related_name='following',
        on_delete=models.CASCADE
    )
