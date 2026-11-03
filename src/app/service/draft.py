from __future__ import annotations

from .scenario import PatchScenario, get_scenario, update_scenario
from ..domain import DraftManager, Draft
from .helper import Err, Ok, Result, Severity, validate_fields
from time import monotonic, sleep
from threading import Thread

manager = DraftManager()
DRAFT_IDLE_TIMEOUT = 15 * 60  # 2 часа


def cleanup_idle_draft():
    ''' Удаляем черновики, бездействующие дольше установленного времени '''
    now = monotonic()
    expired = []

    with manager.lock:
        for scenario_id, draft in list(manager._drafts.items()):
            if now - draft.last_activity >= DRAFT_IDLE_TIMEOUT:
                expired.append((scenario_id, draft.owner_id))

    for scenario_id, owner_id in expired:
        res = save_draft(user_id=owner_id, scenario_id=scenario_id)
        if not res:
            continue
        with manager.lock:
            draft = manager._drafts.get(scenario_id)
            if draft is None or draft.owner_id != owner_id:
                continue
            if now - draft.last_activity >= DRAFT_IDLE_TIMEOUT:
                manager._drafts.pop(scenario_id)


def draft_cleanup_worker():
    while True:
        sleep(60)
        cleanup_idle_draft()


def start_draft_cleanup():
    Thread(
        target=draft_cleanup_worker,
        daemon=True
    ).start()


def open_draft(*, user_id, scenario_id) -> Result[Draft]:
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)
    if type(scenario_id) is not int:
        return Err(meta="scenario_id is not int", severity=Severity.ERROR)

    res = get_scenario(scenario_id=scenario_id, user_id=user_id)
    if not res:
        return Err(meta="Scenario not found", severity=Severity.ERROR)
    scenario = res.value

    id = scenario.id
    version = scenario.format_version
    title = scenario.title
    actor1 = scenario.actor1
    actor2 = scenario.actor2
    target1 = scenario.target1
    target2 = scenario.target2
    context1 = scenario.context1
    context2 = scenario.context2
    doc1 = scenario.document1
    doc2 = scenario.document2

    with manager.lock:
        for _, draft in list(manager._drafts.items()):
            if draft.scenario_id == id:
                return Ok(value=manager._drafts.get(id))

        draft = Draft(
            scenario_id=id,
            owner_id=user_id,
            format_version=version,
            title=title,
            actor1=actor1,
            actor2=actor2,
            target1=target1,
            target2=target2,
            context1=context1,
            context2=context2,
            doc1=doc1,
            doc2=doc2,
        )

        manager._drafts[id] = draft

        return Ok(value=draft)


def update_draft(*, user_id, scenario_id, patch: PatchScenario, revision) -> Result[int]:
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)
    if type(scenario_id) is not int:
        return Err(meta="scenario_id is not int", severity=Severity.ERROR)
    if type(patch) is not PatchScenario:
        return Err(meta="patch is not PatchScenario", severity=Severity.ERROR)
    if type(revision) is not int:
        return Err(meta="revision is not int", severity=Severity.ERROR)

    # отправляем patch fields на валидацию и обрабатываем результат
    res = validate_fields(
        scenario_title=patch.title, scenario_version=patch.version, scenario_actor1=patch.actor1,
        scenario_actor2=patch.actor2, scenario_target1=patch.target1, scenario_target2=patch.target2,
        scenario_context1=patch.context1, scenario_context2=patch.context2, scenario_doc1=patch.doc1,
        scenario_doc2=patch.doc2
    )

    res_title = res['scenario_title']['checked']
    res_version = res['scenario_version']['checked']
    res_actor1 = res['scenario_actor1']['checked']
    res_actor2 = res['scenario_actor2']['checked']
    res_target1 = res['scenario_target1']['checked']
    res_target2 = res['scenario_target2']['checked']
    res_context1 = res['scenario_context1']['checked']
    res_context2 = res['scenario_context2']['checked']
    res_doc1 = res['scenario_doc1']['checked']
    res_doc2 = res['scenario_doc2']['checked']

    errors = []

    for x in [
        res_title, res_version, res_actor1, res_actor2, res_target1,
        res_target2, res_context1, res_context2, res_doc1, res_doc2
    ]:
        if not x:
            errors.append(x.meta)

    if errors:
        errors = 'Validation error: ' + ' | '.join(errors)
        return Err(meta=errors, severity=Severity.ERROR)

    title = res['scenario_title']['normal'].value
    version = res['scenario_version']['normal'].value
    actor1 = res['scenario_actor1']['normal'].value
    actor2 = res['scenario_actor2']['normal'].value
    target1 = res['scenario_target1']['normal'].value
    target2 = res['scenario_target2']['normal'].value
    context1 = res['scenario_context1']['normal'].value
    context2 = res['scenario_context2']['normal'].value
    doc1 = res['scenario_doc1']['normal'].value
    doc2 = res['scenario_doc2']['normal'].value

    with manager.lock:
        draft = manager._drafts.get(scenario_id)
        if draft is None:
            return Err(meta="draft not found", severity=Severity.INFO)
        if draft.owner_id != user_id:
            return Err(meta="draft not found", severity=Severity.INFO)
        if draft.revision != revision:
            return Err(meta="incorrect revision", severity=Severity.INFO)

        changed = False
        if title is not None:
            changed = True
            draft.title = title
        if actor1 is not None:
            changed = True
            draft.actor1 = actor1
        if actor2 is not None:
            changed = True
            draft.actor2 = actor2
        if target1 is not None:
            changed = True
            draft.target1 = target1
        if target2 is not None:
            changed = True
            draft.target2 = target2
        if context1 is not None:
            changed = True
            draft.context1 = context1
        if context2 is not None:
            changed = True
            draft.context2 = context2
        if doc1 is not None:
            changed = True
            draft.doc1 = doc1
        if doc2 is not None:
            changed = True
            draft.doc2 = doc2

        if changed:
            draft.revision += 1
            draft.last_activity = monotonic()

        return Ok(value=draft.revision)


def save_draft(*, user_id, scenario_id) -> Result:
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)
    if type(scenario_id) is not int:
        return Err(meta="scenario_id is not int", severity=Severity.ERROR)

    with manager.lock:
        draft = manager._drafts.get(scenario_id)
        if draft is None:
            return Err(meta="draft not found", severity=Severity.INFO)
        if draft.owner_id != user_id:
            return Err(meta="draft not found", severity=Severity.INFO)

        patch = PatchScenario(
            title=draft.title,
            version=draft.format_version,
            actor1=draft.actor1,
            actor2=draft.actor2,
            target1=draft.target1,
            target2=draft.target2,
            context1=draft.context1,
            context2=draft.context2,
            doc1=draft.doc1,
            doc2=draft.doc2,
        )

    res = update_scenario(user_id=user_id, scenario_id=scenario_id, patch=patch)
    if not res:
        return Err(meta=f"{res.meta}", severity=Severity.ERROR)

    return Ok()


def delete_draft(*, scenario_id, user_id) -> Result:
    if type(user_id) is not int:
        return Err(meta="user_id is not int", severity=Severity.ERROR)
    if type(scenario_id) is not int:
        return Err(meta="scenario_id is not int", severity=Severity.ERROR)

    with manager.lock:
        draft = manager._drafts.get(scenario_id)
        if draft is None:
            return Err(meta="draft not found", severity=Severity.INFO)
        if draft.owner_id != user_id:
            return Err(meta="draft not found", severity=Severity.INFO)

        manager._drafts.pop(scenario_id)

        return Ok()