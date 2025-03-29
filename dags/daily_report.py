import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

import io
import os
import base64
from telegram import Bot
import asyncio

from CH import Getch
from datetime import datetime, timedelta
from airflow.decorators import dag, task


# Дефолтные параметры, которые прокидываются в таски
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': '2025-01-01'
}

# Интервал запуска DAG
schedule_interval = '0 11 * * *'

# База данных, которая будет использоваться во всех запросах
db = os.environ.get('CH_DB_NAME')

@dag(default_args=default_args, schedule_interval=schedule_interval, catchup=False)
def report_for_app():
    
    @task
    # средний DAU использования приложения и сравнение текущего дня с предыдущим
    def get_DAU():
        query = f'''
        SELECT
            date, DAU,
            AVG(DAU) OVER(ORDER BY date) AS avg_DAU
          FROM

            (SELECT
                date, count(user_id) AS DAU
               FROM

                (SELECT 
                    DISTINCT toDate(time) as date, user_id
                   FROM {db}.feed_actions
                ) AS t1

               JOIN

                (SELECT 
                    DISTINCT toDate(time) as date, user_id
                   FROM {db}.message_actions
                ) AS t2
              USING user_id, date
              GROUP BY date) AS main_table

         WHERE date < today()
         ORDER BY date DESC
         LIMIT 2        
        '''

        DAU_data = Getch(query).df
        DAU_data['avg_DAU'] = DAU_data['avg_DAU'].round(2)
        
        current_DAU  = DAU_data['avg_DAU'][0]
        previous_DAU = DAU_data['avg_DAU'][1]
        
        diff = current_DAU - previous_DAU
        growth = round(diff / previous_DAU * 100, 2)
        if growth > 0:
            growth = f'+{growth}'

        DAU_msg = f"Текущий показатель DAU: {current_DAU}\nПредыдущий показатель DAU: {previous_DAU}\nИзменение: {growth}%"   
        return DAU_msg

    @task
    # какая часть пользователей использует оба сервиса в приложении (текущее и предыдущее значения)
    def get_use_both_services():
        query = f'''
        WITH user_counts AS (
            SELECT uniqExact(t1.user_id) FILTER (WHERE t1.user_id != 0 AND t2.user_id != 0 AND toDate(time) < today() - 1) as prev_day,
                   uniqExact(t1.user_id, t2.user_id) FILTER (WHERE toDate(time) < today() - 1) as prev_all_users,
                   uniqExact(t1.user_id) FILTER (WHERE t1.user_id != 0 AND t2.user_id != 0 AND toDate(time) < today()) as cur_day,
                   uniqExact(t1.user_id, t2.user_id) FILTER (WHERE toDate(time) < today()) as cur_all_users
              FROM {db}.feed_actions t1
              FULL JOIN {db}.message_actions t2
                ON t1.user_id = t2.user_id
        )

        SELECT round(prev_day / prev_all_users, 3) * 100 as prev_percentage,
               round(cur_day / cur_all_users , 3) * 100 as cur_percentage
          FROM user_counts
        '''

        use_both_data = Getch(query).df
        prev_value = use_both_data['prev_percentage'][0]
        cur_value  = use_both_data['cur_percentage'][0]
        
        use_both_msg  = f"Какая часть пользователей использует оба сервиса.\nТекущее значение: {cur_value}% пользователей\nПредыдущее значение: {prev_value}% пользователей"
        return use_both_msg

    @task
    # как изменяется retention 7 дня по источникам (одна когорта определяется как вчерашняя дата минус 7 дней, вторая — как позавчерашняя дата минус 7 дней)
    def get_day_7_retention():
        query = f'''
        -- таблица действий пользователей по всему приложению за неделю
        WITH app_users AS (
            -- даты действий пользователей в ленте новостей за неделю
            SELECT user_id, source, date
              FROM (


                SELECT DISTINCT user_id, source, toDate(time) AS date
                  FROM {db}.feed_actions
                 WHERE toDate(time) BETWEEN '2024-09-30'::date - 9 AND '2024-09-30'::date - 1
              ) AS feed

              FULL JOIN (

                -- даты действий пользователей в мессенджере за неделю
                SELECT DISTINCT user_id, source, toDate(time) AS date
                  FROM {db}.message_actions
                 WHERE toDate(time) BETWEEN '2024-09-30'::date - 9 AND '2024-09-30'::date - 1
              ) AS messages

             USING user_id, source, date
        )


        -- считаю retention
        SELECT start_date AS cohort, source,
               ROUND(num_users / start_date_users * 100, 2) AS day_7_retention
          FROM (

        -- считаю количество активных юзеров в стартовый день и последующие
            SELECT start_date, date, source,
                   COUNT(1) AS num_users,
                   MAX(num_users) OVER(partition by start_date, source) AS start_date_users
              FROM (

                -- дата первого использования
                SELECT user_id, source,
                       MIN(date) AS start_date
                  FROM app_users
                 GROUP BY user_id, source
                 ) AS start_dates

              JOIN (

                -- все даты использования
                SELECT DISTINCT user_id, source, date
                  FROM app_users
                ) AS action_dates

             USING user_id
             GROUP BY start_date, date, source
             ) AS main_table
         WHERE date - start_date = 7
         ORDER BY cohort, source
        '''

        day_7_retenion_data = Getch(query).df

        fig, axes = plt.subplots(1, 1, figsize=(20, 7))
        sns.barplot(day_7_retenion_data, x='cohort', y='day_7_retention', hue='source')
        axes.set_title('Сравнение retention 7 дня по источнику')

        plot_object = io.BytesIO()
        fig.savefig(plot_object, format='png')
        plot_object.seek(0)
        img_base64 = base64.b64encode(plot_object.getvalue()).decode('utf-8')
        plt.close(fig)

        return img_base64

    @task
    def send_report(DAU_msg, use_both_msg, plot_object):     
        # отправляю через бота сообщение и график в чат
        bot = Bot(token=os.environ.get('TOKEN'))
        
        async def send_messages():
            chat_id = os.environ.get('CHAT_ID')
            await bot.sendMessage(chat_id=chat_id, text=f"Отчёт по приложению\n\n{DAU_msg}\n\n{use_both_msg}")
            await bot.sendPhoto(chat_id=chat_id, photo=base64.b64decode(plot_object))

        asyncio.run(send_messages())
        
    
    DAU_msg = get_DAU()
    use_both_msg = get_use_both_services()
    plot_object = get_day_7_retention()
    send_report(DAU_msg, use_both_msg, plot_object)
report_for_app = report_for_app()
