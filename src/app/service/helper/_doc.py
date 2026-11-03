from __future__ import annotations

import re
from .result import Ok, Err, Result, Severity

# Дерево, которое пишет наш TipTap (getJSON): узлы doc, paragraph, heading,
# text, hardBreak, bulletList, orderedList, listItem и метки bold, italic,
# strike, underline, link. Пустой content TipTap опускает; {type: doc, content: []}
# остаётся допустимым — так в базе лежит ещё не открытый сценарий.

_BLOCKS = frozenset({'paragraph', 'heading', 'bulletList', 'orderedList'})
_INLINES = frozenset({'text', 'hardBreak'})
_PLAIN_MARKS = frozenset({'bold', 'italic', 'strike', 'underline'})
_LINK_ATTRS = frozenset({'href', 'target', 'rel', 'class', 'title'})
_LINK_REL = 'noopener noreferrer nofollow'
_ORDERED_LIST_TYPES = frozenset({None, '1', 'a', 'A', 'i', 'I'})
_HREF = re.compile(r'^https?://[^\s\\<>\'"]+$', re.IGNORECASE)
_MAX_DEPTH = 32
_MAX_HREF = 2048

_NODE_KEYS = {
    'doc': frozenset({'type', 'content'}),
    'paragraph': frozenset({'type', 'content'}),
    'heading': frozenset({'type', 'attrs', 'content'}),
    'text': frozenset({'type', 'text', 'marks'}),
    'hardBreak': frozenset({'type', 'marks'}),
    'bulletList': frozenset({'type', 'content'}),
    'orderedList': frozenset({'type', 'attrs', 'content'}),
    'listItem': frozenset({'type', 'content'}),
}
_REQUIRED_KEYS = {
    'doc': frozenset({'type'}),
    'paragraph': frozenset({'type'}),
    'heading': frozenset({'type', 'attrs'}),
    'text': frozenset({'type', 'text'}),
    'hardBreak': frozenset({'type'}),
    'bulletList': frozenset({'type', 'content'}),
    'orderedList': frozenset({'type', 'attrs', 'content'}),
    'listItem': frozenset({'type', 'content'}),
}


def _doc_err(path: str, message: str) -> Err:
    if path:
        message = f'{path}: {message}'
    return Err(meta=message, severity=Severity.INFO)


def _join(path: str, suffix: str) -> str:
    return suffix if path == '' else f'{path}.{suffix}'


def _keys(node: dict, node_type: str, path: str) -> Err | None:
    keys = set(node)
    allowed = _NODE_KEYS[node_type]
    if not _REQUIRED_KEYS[node_type] <= keys or not keys <= allowed:
        return _doc_err(path, f'{node_type} has unexpected keys')
    return None


def _content_list(node: dict, path: str, *, required: bool) -> tuple[list | None, Err | None]:
    if 'content' not in node:
        if required:
            return None, _doc_err(path, 'content is required')
        return [], None
    content = node['content']
    if type(content) is not list:
        return None, _doc_err(path, 'content must be a list')
    if required and len(content) == 0:
        return None, _doc_err(path, 'content must not be empty')
    return content, None


def _check_href(href: object, path: str) -> Err | None:
    if type(href) is not str:
        return _doc_err(path, 'href is not a string')
    if len(href) > _MAX_HREF or _HREF.fullmatch(href) is None:
        return _doc_err(path, 'href must be an http or https url')
    if any(ord(char) < 32 or ord(char) == 127 for char in href):
        return _doc_err(path, 'href must be an http or https url')
    return None


def _check_link_attrs(attrs: object, path: str) -> Err | None:
    attr_path = _join(path, 'attrs')
    if type(attrs) is not dict or set(attrs) != _LINK_ATTRS:
        return _doc_err(attr_path, 'link attrs must be href, target, rel, class, title')
    error = _check_href(attrs['href'], _join(attr_path, 'href'))
    if error is not None:
        return error
    if attrs['target'] != '_blank':
        return _doc_err(_join(attr_path, 'target'), 'target must be _blank')
    if attrs['rel'] != _LINK_REL:
        return _doc_err(_join(attr_path, 'rel'), 'rel is not allowed')
    if attrs['class'] is not None:
        return _doc_err(_join(attr_path, 'class'), 'class must be null')
    if attrs['title'] is not None:
        return _doc_err(_join(attr_path, 'title'), 'title must be null')
    return None


def _check_marks(marks: object, path: str) -> Err | None:
    if type(marks) is not list:
        return _doc_err(path, 'marks must be a list')
    seen = set()
    for index, mark in enumerate(marks):
        mark_path = _join(path, f'marks[{index}]')
        if type(mark) is not dict:
            return _doc_err(mark_path, 'mark is not a dict')
        mark_type = mark.get('type')
        if type(mark_type) is not str:
            return _doc_err(mark_path, 'mark type is not a string')
        if mark_type in seen:
            return _doc_err(mark_path, f'duplicate mark {mark_type}')
        seen.add(mark_type)
        if mark_type in _PLAIN_MARKS:
            if set(mark) != {'type'}:
                return _doc_err(mark_path, f'{mark_type} must contain only type')
            continue
        if mark_type == 'link':
            if set(mark) != {'type', 'attrs'}:
                return _doc_err(mark_path, 'link must contain type and attrs')
            error = _check_link_attrs(mark['attrs'], mark_path)
            if error is not None:
                return error
            continue
        return _doc_err(mark_path, f'unknown mark {mark_type}')
    return None


def _check_children(children: list, path: str, allowed: frozenset[str], depth: int) -> Err | None:
    for index, child in enumerate(children):
        child_path = _join(path, f'content[{index}]')
        error = _check_document(child, child_path, allowed, depth + 1)
        if error is not None:
            return error
    return None


def _check_document(node: object, path: str = '', allowed: frozenset[str] | None = None, depth: int = 0) -> Err | None:
    ''' Проверяет дерево документа TipTap, не изменяя его '''
    if depth > _MAX_DEPTH:
        return _doc_err(path, 'nesting exceeds 32')
    if allowed is None:
        allowed = frozenset({'doc'})
    if type(node) is not dict:
        return _doc_err(path, 'node is not a dict')
    node_type = node.get('type')
    if type(node_type) is not str:
        return _doc_err(path, 'type is not a string')
    if node_type not in _NODE_KEYS:
        return _doc_err(path, f'unknown type {node_type}')
    if node_type not in allowed:
        return _doc_err(path, f'type {node_type} is not allowed')
    error = _keys(node, node_type, path)
    if error is not None:
        return error

    if node_type in {'text', 'hardBreak'}:
        if node_type == 'text':
            if type(node['text']) is not str or node['text'] == '':
                return _doc_err(path, 'text must be a non-empty string')
        if 'marks' in node:
            return _check_marks(node['marks'], path)
        return None

    if node_type == 'heading':
        attrs = node['attrs']
        if type(attrs) is not dict or set(attrs) != {'level'} or type(attrs.get('level')) is not int or attrs['level'] != 1:
            return _doc_err(path, 'heading attrs.level must be 1')
        children, error = _content_list(node, path, required=False)
        if error is not None:
            return error
        return _check_children(children, path, _INLINES, depth)

    if node_type == 'orderedList':
        attrs = node['attrs']
        attr_path = _join(path, 'attrs')
        if type(attrs) is not dict or set(attrs) != {'start', 'type'}:
            return _doc_err(attr_path, 'orderedList attrs must be start and type')
        if type(attrs['start']) is not int or attrs['start'] < 1:
            return _doc_err(_join(attr_path, 'start'), 'start must be an integer from 1')
        if attrs['type'] not in _ORDERED_LIST_TYPES:
            return _doc_err(_join(attr_path, 'type'), 'type is not allowed')

    children, error = _content_list(node, path, required=node_type in {'bulletList', 'orderedList', 'listItem'})
    if error is not None:
        return error

    if node_type == 'listItem':
        if type(children[0]) is not dict or children[0].get('type') != 'paragraph':
            return _doc_err(_join(path, 'content[0]'), 'listItem must start with a paragraph')
        return _check_children(children, path, _BLOCKS, depth)
    if node_type == 'paragraph':
        return _check_children(children, path, _INLINES, depth)
    if node_type in {'bulletList', 'orderedList'}:
        return _check_children(children, path, frozenset({'listItem'}), depth)
    return _check_children(children, path, _BLOCKS, depth)


def valid_doc(value: object, name: str) -> Result:
    ''' Проверяет, что документ это dict или отсутствующее поле '''
    if value is None:
        return Ok(meta='value is None')
    if not isinstance(value, dict):
        return Err(meta='value is not a dict', severity=Severity.INFO)
    return Ok(meta=f'{name} successfully')


def normal_doc(value: object, name: str) -> Result:
    ''' Возвращает документ как есть '''
    if value is None:
        return Ok(value=None, meta='value is None')
    return Ok(value=value, meta=f'{name} successfully')


def check_doc(value: object, name: str) -> Result:
    ''' Проверяет структуру документа '''
    if value is None:
        return Ok(meta='value is None')
    error = _check_document(value)
    if error is not None:
        return error
    return Ok(meta=f'{name} successfully')
