"""
For use with thevoid

"""

import math
import time
import json
import logging
import functools
import statistics as stats
from typing import List, Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import asyncpg
from discord import Invite, Message


class DBPerformance:

    def __init__(self):
        self.time = defaultdict(list)

    def avg(self, key: str):
        return stats.mean(self.time[key])

    def all_avg(self):
        avgs = {}
        for key, value in self.time.items():
            avgs[key] = stats.mean(value)
        return avgs

    def stats(self):
        statistics = {}
        for key, value in self.time.items():
            loop_stats = {}
            try:
                loop_stats['avg'] = stats.mean(value)
            except stats.StatisticsError:
                loop_stats['avg'] = -1

            try:
                loop_stats['med'] = stats.median(value)
            except stats.StatisticsError:
                loop_stats['med'] = -1

            try:
                loop_stats['max'] = max(value)
            except stats.StatisticsError:
                loop_stats['max'] = -1

            try:
                loop_stats['min'] = min(value)
            except stats.StatisticsError:
                loop_stats['min'] = -1

            loop_stats['calls'] = len(value)

            statistics[key] = loop_stats
        return statistics


db_perf = DBPerformance()

async def create_db_pool(uri: str) -> asyncpg.pool.Pool:

    # FIXME: Error Handling
    async def init_connection(conn):
        await conn.set_type_codec('json',
                                  encoder=json.dumps,
                                  decoder=json.loads,
                                  schema='pg_catalog')

    pool: asyncpg.pool.Pool = await asyncpg.create_pool(uri, init=init_connection)

    return pool


def db_deco(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            response = await func(*args, **kwargs)
            end_time = time.perf_counter()
            db_perf.time[func.__name__].append((end_time - start_time) * 1000)

            if len(args) > 1:
                logging.debug("DB Query {} from {} in {:.3f} ms.".format(func.__name__, args[1], (end_time - start_time) * 1000))
            else:
                logging.debug("DB Query {} in {:.3f} ms.".format(func.__name__, (end_time - start_time) * 1000))
            return response
        except asyncpg.exceptions.PostgresError:
            logging.exception("Error attempting database query: {} for server: {}".format(func.__name__, args[1]))
    return wrapper





@dataclass
class VoidChannel:
    server_id: int
    channel_id: int
    enabled: bool
    delete_after: float


@db_deco
async def is_void_ch_in_db(pool, sid: int, channel_id: int):
    async with pool.acquire() as conn:
        response = await conn.fetchval("select exists(select 1 from void_channels where server_id = $1 AND channel_id = $2)", sid, channel_id)
        return response


@db_deco
async def add_void_ch(pool, sid: int, channel_id: int, enabled: bool, delete_after: float):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO void_channels(server_id, channel_id, enabled, delete_after) VALUES($1, $2, $3, $4)",
            sid, channel_id, enabled, delete_after)


@db_deco
async def remove_void_ch(pool, sid: int, channel_id: int):
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM void_channels WHERE server_id = $1 AND channel_id = $2", sid, channel_id)


@db_deco
async def get_all_void_channel(pool) -> List[VoidChannel]:
    async with pool.acquire() as conn:
        raw_rows = await conn.fetch('SELECT * FROM void_channels')
        return [VoidChannel(**row) for row in raw_rows]


@db_deco
async def get_void_channels_for_guild(pool, sid: int) -> List[VoidChannel]:
    async with pool.acquire() as conn:
        raw_rows = await conn.fetch('SELECT * FROM void_channels WHERE server_id = $1', sid)
        return [VoidChannel(**row) for row in raw_rows]


@db_deco
async def get_void_channel(pool, channel_id: int) -> Optional[VoidChannel]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT * FROM void_channels WHERE channel_id = $1', channel_id)
        return VoidChannel(**row) if row else None



@db_deco
async def toggle_void_ch(pool, sid: int, channel_id: int, enabled: bool):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE void_channels SET enabled = $1 WHERE server_id = $2 AND channel_id = $3", enabled, sid, channel_id)


@db_deco
async def set_void_delete_time(pool, sid: int, channel_id: int, delete_after: float):
    async with pool.acquire() as conn:
        await conn.execute("UPDATE void_channels SET delete_after = $1 WHERE server_id = $2 AND channel_id = $3", delete_after, sid, channel_id)



async def create_tables(pool):
    # Create servers table
    async with pool.acquire() as conn:
        await conn.execute('''
                           CREATE TABLE if not exists void_channels(
                               server_id       BIGINT,
                               channel_id      BIGINT,
                               enabled         BOOLEAN NOT NULL DEFAULT TRUE,
                               delete_after    FLOAT8,
                               PRIMARY KEY (server_id, channel_id)
                           )
                       ''')


