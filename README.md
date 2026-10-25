# Блогикум — финальный проект

Проект продолжает выполненную работу из `ap-django2`: модели публикаций,
категорий и местоположений, административная панель и фильтрация публикаций.
Добавлены регистрация и профили пользователей, публикации с изображениями,
отложенная публикация, комментарии, редактирование и удаление своих материалов,
пагинация по 10 записей и страницы ошибок. Шаблоны скопированы из прекода
финального задания без изменений.

## Запуск

Из папки `django-sprint4` (Python 3.12):

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python blogicum/manage.py migrate
python blogicum/manage.py loaddata db.json  # необязательно: примеры публикаций
python blogicum/manage.py createsuperuser
python blogicum/manage.py runserver
```

Сайт: http://127.0.0.1:8000/, панель администратора: http://127.0.0.1:8000/admin/.
Категории и местоположения создаются через панель администратора. Пользователи
регистрируются по адресу `/auth/registration/` и создают посты на `/posts/create/`.
На странице `/profile/<username>/` автор видит все свои записи; остальные
посетители видят только опубликованные записи с наступившей датой публикации
и опубликованной категорией.

Изображения сохраняются в `blogicum/media/`, письма восстановления пароля —
в `blogicum/sent_emails/`. Обе папки, база SQLite и виртуальное окружение
исключены из Git. Страницы ошибок 404 и 500 отображаются при `DEBUG = False`.

## Проверки

```bash
python -m pytest
python blogicum/manage.py test blog
python blogicum/manage.py check
python blogicum/manage.py makemigrations --check --dry-run
python -m flake8 blogicum
```
