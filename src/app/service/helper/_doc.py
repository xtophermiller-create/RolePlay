from __future__ import annotations

from .result import Ok, Err, Result, Severity

DOC_NODE_KEYS = frozenset({'type', 'content'})
DOC_STRING_TYPES = frozenset({'heading', 'text', 'image'})
DOC_NONE_TYPES = frozenset({'hardBreak'})
DOC_LIST_CHILDREN = {
    'doc': frozenset({'heading', 'paragraph', 'image', 'numList', 'markedList', 'section'}),
    'paragraph': frozenset({'text', 'hardBreak'}),
    'numList': frozenset({'paragraph'}),
    'markedList': frozenset({'paragraph'}),
    'section': frozenset({'heading', 'paragraph', 'image', 'numList', 'markedList', 'section'}),
}
DOC_TYPES = frozenset(DOC_LIST_CHILDREN) | DOC_STRING_TYPES | DOC_NONE_TYPES
MAX_SECTION_DEPTH = 5
MAX_ROOT_SECTIONS = 4


def _doc_err(path: str, message: str) -> Err:
    if path:
        message = f'{path}: {message}'
    return Err(meta=message, severity=Severity.INFO)


def _check_document(node: object, path: str = '', allowed: frozenset[str] | None = None, section_depth: int = 0) -> Err | None:
    ''' Проверяет дерево документа, не изменяя его '''
    if allowed is None:
        allowed = frozenset({'doc'})
    if type(node) is not dict:
        return _doc_err(path, 'node is not a dict')
    if set(node) != DOC_NODE_KEYS:
        return _doc_err(path, 'node must contain exactly keys type and content')
    node_type = node['type']
    content = node['content']
    if type(node_type) is not str:
        return _doc_err(path, 'type is not a string')
    if node_type not in DOC_TYPES:
        return _doc_err(path, f'unknown type {node_type}')
    if node_type not in allowed:
        return _doc_err(path, f'type {node_type} is not allowed')
    if node_type == 'section':
        section_depth += 1
        if section_depth > MAX_SECTION_DEPTH:
            return _doc_err(path, 'section nesting exceeds 5')
    if node_type in DOC_NONE_TYPES:
        if content is not None:
            return _doc_err(path, 'content must be None')
        return None
    if node_type in DOC_STRING_TYPES:
        if type(content) is not str:
            return _doc_err(path, 'content must be a string')
        return None
    if type(content) is not list:
        return _doc_err(path, 'content must be a list')
    section_count = 0
    for index, child in enumerate(content):
        child_path = f'content[{index}]' if path == '' else f'{path}.content[{index}]'
        if node_type == 'doc' and type(child) is dict and child.get('type') == 'section':
            section_count += 1
            if section_count > MAX_ROOT_SECTIONS:
                return _doc_err(child_path, 'root document contains more than 4 sections')
        error = _check_document(child, child_path, DOC_LIST_CHILDREN[node_type], section_depth)
        if error is not None:
            return error
    return None


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
