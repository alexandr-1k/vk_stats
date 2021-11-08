import itertools
import sqlite3
from requests import get
from datetime import datetime
import time
from allauth.socialaccount.models import SocialToken
import pandas as pd
from .settings import DATABASES


def get_access_token(request) -> str:
    """ Получаю access token для соответствующего пользователя"""

    return str(SocialToken.objects.get(account__user=request.user, account__provider='vk'))


def get_empty_data(message: str) -> dict:
    """ Возвращает словарь с нулями для каждой из метрик. Далее при получени
    средних значений будет использоваться такой формат для вывода на фронт"""

    l = [0] * 5
    return {'time_interval': l, 'posts_count': l, 'likes_requested': l, 'reposts_requested': l, 'comments_requested': l,
            'attch_count': l, 'error': message}


def get_db_engine_and_cursor():
    """ Вовзвращает объекты, связанные с локальной базой db.sqlite3"""

    engine = sqlite3.connect(DATABASES['default']['NAME'])
    return engine, engine.cursor()


def save_to_db(dataframe: pd.DataFrame, token: str) -> None:
    """ Создаю отдельную таблицу в базе с соответвующими столбцами из pd.Dataframe"""

    engine, cursor = get_db_engine_and_cursor()
    table_name = f'result_{token[:-8]}'
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    dataframe.to_sql(table_name, con=engine)


def extract_data_from_db(request) -> pd.DataFrame:
    """ Достаю таблицу с результатами из базы и отправляю на сохранение. После
    получения удаляю ее в базе"""

    engine, cursor = get_db_engine_and_cursor()

    token = get_access_token(request)
    table_name = f'result_{token[:-8]}'

    extracted = pd.read_sql_query(f"SELECT * FROM {table_name}", engine)

    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    return extracted


def process_data(data, params, averaging_window):
    """ Основной цикл, в котором парсится json. Тут же пишу результат в базу,
    а после возвращаю результат на фронт для построения графиков"""

    if len(data[0]) == 2:  # nothing is required
        return get_empty_data('Nothing is requested!')

    valid_posts = list(
        filter(lambda d: data[-1]['dates'][d] > params['date_requested'], range(data[-1]['total_posts'])))

    for _key in data[-1].keys():
        if isinstance(data[-1][_key], list):
            data[-1][_key] = data[-1][_key][:valid_posts[-1] + 1]

    data[-1]['total_posts'] = len(data[-1]['dates'])

    requested_data = dict(itertools.islice(params.items(), 1, len(params) - 3))
    given_flags = list(filter(lambda x: requested_data[x] == '1', requested_data.keys()))
    given_flags.append('dates')

    concatenated_output = {k: [] for k in given_flags}
    total_posts = 0

    if 'attch_requested' in params and params['attch_requested'] == '1':
        concatenated_output['attch_count'] = []

    for chunk in data:
        total_posts += chunk['total_posts']

        for requested in chunk:

            if isinstance(chunk[requested], list) and requested != 'attch_requested':
                concatenated_output[requested].extend(chunk[requested])

        if 'attch_requested' in chunk:

            for att_list in chunk['attch_requested']:
                if att_list is None:
                    concatenated_output['attch_requested'].append("No attachment")
                    concatenated_output['attch_count'].append(0)
                    continue

                post_attachments = []
                for one_att in att_list:

                    if one_att['type'] == 'photo':
                        post_attachments.append(f'{one_att["type"]}: {one_att["photo"]["sizes"][-1]["url"]}')
                    elif one_att['type'] == 'link':
                        post_attachments.append(f'{one_att["type"]}: {one_att["link"]["url"]}')
                    elif one_att['type'] == 'video':
                        post_attachments.append(f'{one_att["type"]}: {one_att["video"]["track_code"]}')
                    elif one_att['type'] == 'audio':
                        post_attachments.append(f'{one_att["type"]}: {one_att["audio"]["url"]}')
                    else:
                        post_attachments.append(f'{one_att["type"]}: no link ')

                concatenated_output['attch_requested'].append("\n".join(post_attachments))
                concatenated_output['attch_count'].append(len(post_attachments))

    output = pd.DataFrame(concatenated_output)
    output['dates'] = pd.to_datetime(output['dates'], unit='s') + pd.Timedelta('03:00:00')

    if averaging_window == 'Hours':
        post_count = output.groupby(output['dates'].dt.hour).count()
        output = output.groupby(output['dates'].dt.hour).mean()
        output['posts_count'] = post_count[post_count.columns[0]]

    elif averaging_window == "Days":
        post_count = output.groupby(output['dates'].dt.dayofweek).count()
        output = output.groupby(output['dates'].dt.dayofweek).mean()
        output['posts_count'] = post_count[post_count.columns[0]]

    elif averaging_window == 'Months':
        post_count = output.groupby(output['dates'].dt.month).count()
        output = output.groupby(output['dates'].dt.month).mean()
        output['posts_count'] = post_count[post_count.columns[0]]

    elif averaging_window == 'Years':
        post_count = output.groupby(output['dates'].dt.year).count()
        output = output.groupby(output['dates'].dt.year).mean()
        output['posts_count'] = post_count[post_count.columns[0]]

    if averaging_window != 'No_window' and 'id_requested' in params and params['id_requested'] == '1':
        del output['id_requested']

    if averaging_window != 'No_window':
        time_interval = output.index.tolist()

        l = [0] * len(time_interval)

        js_chart_items = {'time_interval': time_interval, 'posts_count': l, 'likes_requested': l,
                          'reposts_requested': l,
                          'comments_requested': l, 'attch_count': l, 'error': '0'}

        for column in output.columns:
            if column in js_chart_items:
                js_chart_items[column] = list(output[column].values)
        save_to_db(output, params['access_token'])
        return js_chart_items
    else:
        save_to_db(output, params['access_token'])
        return get_empty_data('No window no charts! But .csv is available!')


def send_requests(params: dict) -> dict:
    """ Отправляю запросы к ВК.
    VK Api позволяет отправлять с ключем пользователя 3 запроса в секунду, при этом
    максимумальное количество постов, которое можно получить за  секунду, равно
    300 (т.к. один wall.get имеет ограничение count=100)

    Хотел сначала отправлять запросы асинхронно через aiohttp, но после решил
    использовать хранимые процедуры для приложения ВК.

    Из минусов: при выборе всего сразу (id поста, text, likes ...) все может упасть
    из-за большого размера пересылаемого response (>5 Mb), если выбрать дату,
    например с начала 2020 года.

    Код хранимой процедуры:

    var ITERS = 25;
    var COUNT = 100;
    var posts = [];
    var req_params = {
        "access_token": Args.token,
        "domain" : Args.domain,
        "offset" : 0,
        "count"  : COUNT,
        "v" : "5.131",
        'date_requested': Args.date_requested,
        '_id': Args.id_requested,
        '_text': Args.text_requested,
        '_attch': Args.attch_requested,
        '_likes': Args.likes_requested,
        '_reposts': Args.reposts_requested,
        '_comments': Args.comments_requested

    };


    var i = 0;
    while(i < ITERS){

        req_params.offset = i*COUNT + ITERS*COUNT*Args.offset;
        var items = API.wall.get(req_params).items;
        var dates = items@.date;
        if (dates[0] < req_params['date_requested']){
          return posts;
        }
        if (items.length == 0) {
            return posts;
        }

        var ids = items@.id;
        var owner_ids = items@.owner_id;
        var tmp = {};

        tmp.total_posts = ids.length;

        if (req_params['_id'] == 1){
          tmp.owner_id = owner_ids[0];
          tmp.id_requested = ids;
        }

         if (req_params['_text'] == 1){
          tmp.text_requested = items@.text;
        }

        if (req_params['_attch'] == 1){
          tmp.attch_requested= items@.attachments;
        }

        if (req_params['_likes'] == 1){
          tmp.likes_requested = items@.likes@.count;
        }

        if (req_params['_reposts'] == 1){
          tmp.reposts_requested = items@.reposts@.count;
        }

        if (req_params['_comments'] == 1){
          tmp.comments_requested = items@.comments@.count;
        }

        tmp.dates = dates;

        posts.push(tmp);
        i = i + 1;
    }
    return posts;
    """

    averaging_window = params.pop('averaging_window')
    necessary_fields = {'offset': 0, 'v': '5.131'}
    params.update(necessary_fields)

    data = []
    r_i = 0
    while True:
        r = get("https://api.vk.com/method/execute.vk_stats_get_posts", params=params)

        json_data = r.json()
        if 'error' in json_data:
            return get_empty_data(json_data['error']['error_msg'])
        else:
            data_from_request = json_data['response']

        if len(data_from_request) == 0 and len(data) == 0:
            return get_empty_data('No data received!')

        data += data_from_request
        r_i += 1
        params['offset'] += 1
        if data_from_request[-1]['dates'][-1] < params['date_requested']:
            break

    return process_data(data, params, averaging_window)


def get_chart_data(request) -> dict:
    """ Меняю дату на UNIX формат, добавляю access token в параметры запроса
    и начинаю отправлять сами запросы через send_requests"""

    input_dict = request.GET.dict()

    params_requested = dict(itertools.islice(input_dict.items(), 2, len(input_dict) - 1))

    input_timestamp = datetime.strptime(params_requested['date_requested'] + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    params_requested['date_requested'] = int(time.mktime(input_timestamp.timetuple()))
    params_requested['access_token'] = get_access_token(request)

    # print(f"\nInput dict: {input_dict}\nParams dict : {params_requested}")

    return send_requests(params_requested)


if __name__ == '__main__':
    pass
