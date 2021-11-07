import itertools
from requests import get
from datetime import datetime
import time
from allauth.socialaccount.models import SocialToken
import asyncio
import pandas as pd


def test_request():
    input_timestamp = datetime.strptime('2021-10-30' + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    unix_time = int(time.mktime(input_timestamp.timetuple()))

    params = {'access_token': 'token token',
              'domain': 'fontanka',
              'offset': '0',
              'v': '5.131',
              'date_requested': unix_time,
              'id_requested': '1',
              'text_requested': '0',
              'attch_requested': '1',
              'likes_requested': '1',
              'reposts_requested': '1',
              'comments_requested': '1',
              }

    r = get("https://api.vk.com/method/execute.vk_stats_get_posts", params=params)
    data = r.json()['response']

    print()

    posts = 0

    if len(data) == 0:
        raise NameError("NO FETCHED DATA!")

    if len(data[0]) == 2:
        raise NameError("NO DATA REQUIRED!")

    valid_posts = list(filter(lambda d: data[-1]['dates'][d] > unix_time, range(data[-1]['total_posts'])))
    for _key in data[-1].keys():
        if isinstance(data[-1][_key], list):
            data[-1][_key] = data[-1][_key][:valid_posts[-1] + 1]

    data[-1]['total_posts'] = len(data[-1]['dates'])

    requested_data = dict(itertools.islice(params.items(), 5, len(params)))
    given_flags = list(filter(lambda x: requested_data[x] == '1', requested_data.keys()))
    given_flags.append('dates')

    concatenated_output = {k: [] for k in given_flags}
    total_posts = 0

    for chunk in data:
        total_posts += chunk['total_posts']

        for requested in chunk:

            if isinstance(chunk[requested], list) and requested != 'attch_requested':
                concatenated_output[requested].extend(chunk[requested])

        if 'attch_requested' in chunk:
            for att_list in chunk['attch_requested']:
                if att_list is None:
                    concatenated_output['attch_requested'].append("No attachment")
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

    dataframe = pd.DataFrame(concatenated_output)
    dataframe['dates'] = pd.to_datetime(dataframe['dates'], unit='s')

    d2 = dataframe.groupby(dataframe['dates'].dt.dayofweek).mean()


def get_empty_data() -> dict:
    l = [0] * 5
    return {'time_interval': l, 'posts': l, 'likes': l, 'reposts': l, 'comments': l, 'attch': l}


def send_requests(token: str, id: str):
    response = get("https://api.vk.com/method/wall.get", params={'access_token': token, 'v': '5.131', 'domain': id})

    pass


def get_chart_data(request) -> dict:

    # input_dict = request.GET.dict()

    input_dict = {'siteId': ['185996874'],
                  'pageId': ['238373189'],
                  'id_input': ['qazws17'],
                  'start_point_input': ['2021-11-13'],
                  'comments_check': ['On'],
                  'averagin_list': ['Years'],
                  'recaptchaResponse': ['']}

    # access_token = str(SocialToken.objects.get(account__user=request.user,
    #                                        account__provider='vk'))

    access_token = "28281e5adccdd12b51793b6fb6abdf67c9e3331c952ed9fc3f1c121b82d9c2eec4d2811d8a5b93006b2d9"

    params_requested = dict(itertools.islice(input_dict.items(), 2, len(input_dict) - 1))

    input_timestamp = datetime.strptime('2021-11-13' + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    input_dict['start_point_input'] = int(time.mktime(input_timestamp.timetuple()))

    send_requests(access_token, params_requested['id_input'])

    return dict()


if __name__ == '__main__':

    get_chart_data(None)
