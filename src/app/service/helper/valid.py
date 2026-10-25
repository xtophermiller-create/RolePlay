from __future__ import annotations

import asyncio
import string
from sqlalchemy.exc import SQLAlchemyError
from ...domain import USER_LENGTH, SCENARIO_LENGTH, SCENARIO_DEFAULT
from .result import Result, Ok, Err, Severity

PUNCTUATION = string.punctuation
WHITESPACE = string.whitespace
LETTERS = string.ascii_letters
UP_LETTER = string.ascii_uppercase
LOW_LETTERS = string.ascii_lowercase
DIGITS = string.digits


async def _validator(plan: dict, kwargs: dict) -> dict:
    ''' Проверяет типизацию и самые базовые требования к данным '''
    async def _login(value):
        if not isinstance(value, str):
            plan['login']['valid'] = Err(meta='value is not a string', severity=Severity.INFO)
            return
        if not value.strip():
            plan['login']['valid'] = Err(meta='Not value', severity=Severity.INFO)
            return
        plan['login']['valid'] = Ok(meta='Login successfully')
        return
    async def _auth_login(value):
        if not isinstance(value, str):
            plan['auth_login']['valid'] = Err(meta='value is not a string', severity=Severity.INFO)
            return
        if not value.strip():
            plan['auth_login']['valid'] = Err(meta='Not value', severity=Severity.INFO)
            return
        plan['auth_login']['valid'] = Ok(meta='Login successfully')
        return
    async def _password(value):
        if not isinstance(value, str):
            plan['password']['valid'] = Err(meta='value is not a string', severity=Severity.INFO)
            return
        if not value.strip():
            plan['password']['valid'] = Err(meta='Not value', severity=Severity.INFO)
            return
        plan['password']['valid'] = Ok(meta='Password successfully')
        return
    async def _scenario_title(value):
        if value is None:
            plan['scenario_title']['valid'] = Ok(meta='value is None')
            return
        if not isinstance(value, str):
            plan['scenario_title']['valid'] = Err(meta='value is not a string', severity=Severity.INFO)
            return
        plan['scenario_title']['valid'] = Ok(meta='Title successfully')
        return
    async def _scenario_version(value):
        if value is None:
            plan['scenario_version']['valid'] = Ok(meta='value is None')
            return
        if not isinstance(value, int):
            plan['scenario_version']['valid'] = Err(meta='value is not a integer', severity=Severity.INFO)
            return
        if not value:
            plan['scenario_version']['valid'] = Err(meta='Not value', severity=Severity.INFO)
            return
        plan['scenario_version']['valid'] = Ok(meta='Version successfully')
        return
    async def _scenario_actor1(value):
        if value is None:
            plan['scenario_actor1']['valid'] = Ok(meta='value is None')
            return
        if not isinstance(value, str):
            plan['scenario_actor1']['valid'] = Err(meta='value is not a string', severity=Severity.INFO)
            return
        plan['scenario_actor1']['valid'] = Ok(meta='Actor1 successfully')
        return
    async def _scenario_actor2(value):
        if value is None:
            plan['scenario_actor2']['valid'] = Ok(meta='value is None')
            return
        if not isinstance(value, str):
            plan['scenario_actor2']['valid'] = Err(meta='value is not a string', severity=Severity.INFO)
            return
        plan['scenario_actor2']['valid'] = Ok(meta='Actor2 successfully')
        return
    async def _scenario_target1(value):

    tasks = []

    for key, val in kwargs.items():
        func_name = plan[str(key)]['function']
        if not func_name:
            plan[str(key)]['valid'] = func_name
            continue
        tasks.append(locals().get(func_name)(val))

    await asyncio.gather(*tasks)

    return plan


async def _normalizer(plan: dict, kwargs: dict) -> dict:
    ''' Нормализует данные '''
    async def _login(value):
        value = value.strip().lower()
        plan['login']['normal'] = Ok(value=value, meta='Login successfully')
        return
    async def _auth_login(value):
        value = value.strip().lower()
        plan['auth_login']['normal'] = Ok(value=value, meta='Login successfully')
        return
    async def _password(value):
        plan['password']['normal'] = Ok(value=value, meta='Password successfully')
        return
    async def _scenario_title(value):
        if value is None:
            plan['scenario_title']['normal'] = Ok(value=None, meta='value is None')
            return
        value = value.strip()
        if not value:
            value = SCENARIO_DEFAULT['TITLE']
        plan['scenario_title']['normal'] = Ok(value=value, meta='Title successfully')
        return
    async def _scenario_version(value):
        if value is None:
            plan['scenario_version']['normal'] = Ok(value=None, meta='value is None')
            return
        plan['scenario_version']['normal'] = Ok(value=value, meta='Version successfully')
        return
    async def _scenario_actor1(value):
        if value is None:
            plan['scenario_actor1']['normal'] = Ok(value=None, meta='value is None')
            return
        value = value.strip()
        if not value:
            plan['scenario_actor1']['normal'] = SCENARIO_DEFAULT['ACTOR1']
        plan['scenario_actor1']['normal'] = Ok(value=value, meta='Actor1 successfully')
        return
    async def _scenario_actor2(value):
        if value is None:
            plan['scenario_actor2']['normal'] = Ok(value=None, meta='value is None')
            return
        value = value.strip()
        if not value:
            plan['scenario_actor2']['normal'] = SCENARIO_DEFAULT['ACTOR2']
        plan['scenario_actor2']['normal'] = Ok(value=value, meta='Actor2 successfully')
        return

    tasks = []

    for key, val in kwargs.items():
        valid = plan[str(key)]['valid']
        if not valid:
            plan[str(key)]['normal'] = valid
            continue
        tasks.append(locals().get(plan[str(key)]['function'])(val))

    await asyncio.gather(*tasks)

    return plan


async def _checker(plan: dict, kwargs: dict) -> dict:
    ''' Проверяет ограничения на чистые данные '''
    async def _login(value):
        symbols = LOW_LETTERS + DIGITS
        for x in value:
            if x not in symbols + '_-.':
                plan['login']['checked'] = Err(meta='value contains prohibited simbols', severity=Severity.INFO)
                return
        if not USER_LENGTH['MIN_LOGIN'] <= len(value) <= USER_LENGTH['MAX_LOGIN']:
            plan['login']['checked'] = Err(meta='value exceeds maximum length', severity=Severity.INFO)
            return
        if value[0] not in symbols:
            plan['login']['checked'] = Err(meta='First symbol in value should be letter', severity=Severity.INFO)
            return
        if value[-1] not in symbols:
            plan['login']['checked'] = Err(meta='Last symbol in value should be letter', severity=Severity.INFO)
            return
        try:

            # транзакция на проверку уникальности логина

        except SQLAlchemyError as e:
            plan['login']['checked'] = Err(meta="Database transaction failed", severity=Severity.CRITICAL)
            return
        except Exception as e:
            plan['login']['checked'] = Err(meta="Unexpected transaction error", severity=Severity.CRITICAL)
            return
        plan['login']['checked'] = Ok(meta='Login successfully')
        return
    async def _auth_login(value):
        symbols = LOW_LETTERS + DIGITS
        for x in value:
            if x not in symbols + '_-.':
                plan['auth_login']['checked'] = Err(meta='value contains prohibited simbols', severity=Severity.INFO)
                return
        if not USER_LENGTH['MIN_LOGIN'] <= len(value) <= USER_LENGTH['MAX_LOGIN']:
            plan['auth_login']['checked'] = Err(meta='value exceeds maximum length', severity=Severity.INFO)
            return
        if value[0] not in symbols:
            plan['auth_login']['checked'] = Err(meta='First symbol in value should be letter', severity=Severity.INFO)
            return
        if value[-1] not in symbols:
            plan['auth_login']['checked'] = Err(meta='Last symbol in value should be letter', severity=Severity.INFO)
            return
        plan['auth_login']['checked'] = Ok(meta='Login successfully')
        return
    async def _password(value):
        symbols = LETTERS + DIGITS + PUNCTUATION
        for x in value:
            if x not in symbols:
                plan['password']['checked'] = Err(meta='value contains prohibited simbols', severity=Severity.INFO)
                return
        if not USER_LENGTH['MIN_PASSWORD'] <= len(value) <= USER_LENGTH['MAX_PASSWORD']:
            plan['password']['checked'] = Err(meta='value exceeds maximum length', severity=Severity.INFO)
            return
        plan['password']['checked'] = Ok(meta='Password successfully')
        return
    async def _scenario_title(value):
        if value is None:
            plan['scenario_title']['checked'] = Ok(meta='value is None')
            return
        symbols = LETTERS + DIGITS + 'йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ' + PUNCTUATION
        for x in value:
            if x not in symbols:
                plan['scenario_title']['checked'] = Err(meta='value contains prohibited simbols', severity=Severity.INFO)
                return
        if not len(value) <= SCENARIO_LENGTH['MAX_TITLE']:
            plan['scenario_title']['checked'] = Err(meta='value exceeds maximum length', severity=Severity.INFO)
            return
        plan['scenario_title']['checked'] = Ok(meta='Title successfully')
        return
    async def _scenario_version(value):
        if value is None:
            plan['scenario_version']['checked'] = Ok(meta='value is None')
            return
        if value < SCENARIO_DEFAULT['version']:
            plan['scenario_version']['checker'] = Err(meta="Scenario version is outdated", severity=Severity.INFO)
            return
        if SCENARIO_DEFAULT['version'] < value:
            plan['scenario_version']['checker'] = Err(meta="Scenario version is not supported", severity=Severity.INFO)
            return
        plan['scenario_version']['checker'] = Ok(meta='Scenario version successfully')
    async def _scenario_actor1(value):
        if value is None:
            plan['scenario_actor1']['checked'] = Ok(meta='value is None')
            return
        symbols = LETTERS + DIGITS + 'йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ' + PUNCTUATION
        for x in value:
            if x not in symbols:
                plan['scenario_actor1']['checked'] = Err(meta='value contains prohibited simbols', severity=Severity.INFO)
                return
        if not len(value) <= SCENARIO_LENGTH['MAX_ACTOR1']:
            plan['scenario_actor1']['checked'] = Err(meta='value exceeds maximum length', severity=Severity.INFO)
            return
        plan['scenario_actor1']['checked'] = Ok(meta='Actor1 successfully')
        return
    async def _scenario_actor2(value):
        if value is None:
            plan['scenario_actor2']['checked'] = Ok(meta='value is None')
            return
        symbols = LETTERS + DIGITS + 'йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ' + PUNCTUATION
        for x in value:
            if x not in symbols:
                plan['scenario_actor2']['checked'] = Err(meta='value contains prohibited simbols', severity=Severity.INFO)
                return
        if not len(value) <= SCENARIO_LENGTH['MAX_ACTOR2']:
            plan['scenario_actor2']['checked'] = Err(meta='value exceeds maximum length', severity=Severity.INFO)
            return
        plan['scenario_actor2']['checked'] = Ok(meta='Actor2 successfully')
        return

    tasks = []

    for key, val in kwargs.items():
        normal = plan[str(key)]['normal']
        if not normal:
            plan[str(key)]['checked'] = normal
            continue
        tasks.append(locals().get(plan[str(key)]['function'])(normal.value))

    await asyncio.gather(*tasks)

    return plan


def validate_fields(**kwargs) -> dict:
    functions = {
        'login': '_login',
        'auth_login': '_auth_login',
        'password': '_password',
        'scenario_title': '_scenario_title',
        'scenario_version': '_scenario_version',
        'scenario_actor1': '_scenario_actor1',
        'scenario_actor2': '_scenario_actor2',
        'scenario_target1': '_scenario_target1',
        'scenario_target2': '_scenario_target2',
        'scenario_context1': '_scenario_context1',
        'scenario_context2': '_scenario_context2',
    }
    results = dict()

    for key, val in kwargs.items():
        func = functions.get(key)
        if func is None:
            results[str(key)] = {'function': Err(meta='No module'), 'valid': None, 'normal': None, 'checked': None}
            continue
        results[str(key)] = {'function': func, 'valid': None, 'normal': None, 'checked': None}

    results = asyncio.run(_validator(results, kwargs))
    results = asyncio.run(_normalizer(results, kwargs))
    results = asyncio.run(_checker(results, kwargs))

    return results