// Страница комнаты: лобби до старта, карточки ролей после.
// Текст — только через textContent, никакого innerHTML.
// Уже нарисованные карточки не пересоздаются: иначе каждое обновление дёргает страницу.
import { createDocumentEditor, setDocument } from './vendor/tiptap.bundle.js'
// «Назад» может поднять страницу из памяти, не спрашивая сервер. Тогда ушедший
// снова получил бы состояние сессии. Повторный запрос упирается в ту же проверку, что и прямая ссылка.
window.addEventListener('pageshow', (event) => {
  if (event.persisted && document.querySelector('[data-room-code]')) {
    window.location.reload()
  }
})

const page = document.querySelector('[data-room-code]')
if (page) {
  start(page)
}

function start(page) {
  const slots = (name) => page.querySelectorAll(`[data-slot="${name}"]`)
  const avatarUrl = page.dataset.avatar || ''
  const crownUrl = page.dataset.crown || ''
  const me = page.dataset.me || ''
  const seatNodes = new Map()
  const playEditors = new Map()

  const setText = (name, value) => {
    const text = value ?? ''
    slots(name).forEach((node) => {
      if (node.textContent !== text) {
        node.textContent = text
      }
    })
  }

  const roleLabel = (role, state) => {
    switch (role) {
      case 'actor1':
        return state.actor1 || 'Роль 1'
      case 'actor2':
        return state.actor2 || 'Роль 2'
      case 'observer':
        return 'Наблюдатель'
      default:
        return 'без роли'
    }
  }

  const avatar = (className, size, title, mine) => {
    const img = document.createElement('img')
    img.className = className + (mine ? ' is-me' : '')
    img.src = avatarUrl
    img.alt = ''
    img.width = size
    img.height = size
    img.draggable = false
    if (title) {
      img.title = title
    }
    return img
  }

  const buildSeat = (player, state) => {
    const seat = document.createElement('article')
    seat.className = 'session-seat' + (player.is_owner ? ' session-seat--host' : '')

    if (player.is_owner && crownUrl) {
      const crown = document.createElement('img')
      crown.className = 'session-seat__crown'
      crown.src = crownUrl
      crown.alt = ''
      crown.width = 42
      crown.draggable = false
      seat.append(crown)
    }

    const wrap = document.createElement('div')
    wrap.className = 'session-seat__avatar-wrap'
    wrap.append(avatar('session-seat__avatar', 88))

    const name = document.createElement('p')
    name.className = 'session-seat__name'
    name.textContent = player.nickname || 'Игрок'
    name.title = name.textContent

    const hint = document.createElement('p')
    hint.className = 'session-seat__hint'
    hint.textContent = roleLabel(player.role, state) + (player.left ? ' · вышел' : '')

    seat.append(wrap, name, hint)
    return seat
  }

  const place = (parent, index, node) => {
    if (parent.children[index] !== node) {
      parent.insertBefore(node, parent.children[index] || null)
    }
  }

  const renderSeats = (state) => {
    const box = page.querySelector('[data-slot="players"]')
    if (!box) {
      return
    }
    const ordered = [...state.players].sort((a, b) => Number(b.is_owner) - Number(a.is_owner))
    const counts = new Map()
    const next = new Set()
    ordered.forEach((player, index) => {
      const base = `${player.is_owner ? '1' : '0'}\u0001${player.nickname || ''}`
      const n = counts.get(base) || 0
      counts.set(base, n + 1)
      const key = `${base}\u0001${n}`
      next.add(key)

      const hintText = roleLabel(player.role, state) + (player.left ? ' · вышел' : '')
      const nameText = player.nickname || 'Игрок'
      let seat = seatNodes.get(key)
      if (!seat) {
        seat = buildSeat(player, state)
        seatNodes.set(key, seat)
      } else {
        const hint = seat.querySelector('.session-seat__hint')
        const name = seat.querySelector('.session-seat__name')
        if (hint && hint.textContent !== hintText) {
          hint.textContent = hintText
        }
        if (name && name.textContent !== nameText) {
          name.textContent = nameText
          name.title = nameText
        }
      }
      place(box, index, seat)
    })

    for (const [key, seat] of seatNodes) {
      if (!next.has(key)) {
        seat.remove()
        seatNodes.delete(key)
      }
    }
  }

  const renderRole = (role, state) => {
    const card = page.querySelector(`[data-role-card="${role}"]`)
    const box = page.querySelector(`[data-role-avatars="${role}"]`)
    const button = page.querySelector(`[data-take="${role}"]`)
    if (!card || !box || !button) {
      return
    }

    const chosen = state.players.filter((player) => player.role === role && !player.left)
    const mine = chosen.some((player) => player.nickname === me)
    const signature = chosen.map((player) => `${player.nickname || ''}\u0001${player.nickname === me ? '1' : '0'}`).join('\n')
    if (box.dataset.signature !== signature) {
      box.dataset.signature = signature
      box.replaceChildren()
      if (chosen.length === 0) {
        const empty = document.createElement('span')
        empty.className = 'session-role__empty'
        empty.textContent = 'Никого'
        box.append(empty)
      } else {
        box.append(...chosen.map((player) => avatar(
          'session-role__avatar',
          36,
          player.nickname || 'Игрок',
          player.nickname === me,
        )))
      }
    }

    const count = page.querySelector(`[data-role-count="${role}"]`)
    if (count) {
      const countText = String(chosen.length)
      count.hidden = chosen.length === 0
      if (count.textContent !== countText) {
        count.textContent = countText
      }
    }

    const actor = role !== 'observer'
    card.classList.toggle('is-ready', actor ? chosen.length === 1 : chosen.length > 0)
    card.classList.toggle('is-conflict', actor && chosen.length > 1)
    const label = mine ? 'Выбрано' : 'Занять'
    const disabled = state.is_started || mine
    if (button.textContent !== label) {
      button.textContent = label
    }
    if (button.disabled !== disabled) {
      button.disabled = disabled
    }
  }

  const showError = (messages) => {
    const items = messages.filter(Boolean)
    page.querySelectorAll('[data-lobby-error]').forEach((list) => {
      const same = list.childElementCount === items.length
        && [...list.children].every((item, index) => item.textContent === items[index])
      if (!same) {
        list.replaceChildren(...items.map((text) => {
          const item = document.createElement('li')
          item.textContent = text
          return item
        }))
      }
      list.hidden = items.length === 0
    })
  }

  const scenarioPopup = page.querySelector('[data-lobby-scenario-popup]')
  const scenarioButton = page.querySelector('[data-lobby-scenario]')
  const startButton = page.querySelector('[data-lobby-start]')
  let scenarioReturn = null

  const closeScenario = () => {
    if (!scenarioPopup || scenarioPopup.hidden) {
      return
    }
    scenarioPopup.hidden = true
    document.body.classList.remove('lobby-popup-open')
    if (scenarioReturn instanceof HTMLElement) {
      scenarioReturn.focus()
    }
  }

  const openScenario = () => {
    if (!scenarioPopup) {
      return
    }
    scenarioReturn = document.activeElement
    scenarioPopup.hidden = false
    document.body.classList.add('lobby-popup-open')
    scenarioPopup.querySelector('.scenarios__back')?.focus()
  }

  scenarioButton?.addEventListener('click', openScenario)
  scenarioPopup?.querySelectorAll('[data-lobby-scenario-close]').forEach((node) => {
    node.addEventListener('click', closeScenario)
  })
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeScenario()
    }
  })

  const render = (state) => {
    setText('status', state.is_started ? 'идёт игра' : 'ожидание')
    setText('title', state.title || 'Лобби')
    setText('actor1', state.actor1 || 'Роль 1')
    setText('actor2', state.actor2 || 'Роль 2')
    setText('target1', (state.target1 || '').trim())
    setText('target2', (state.target2 || '').trim())
    setText('context1', (state.context1 || '').trim())
    setText('context2', (state.context2 || '').trim())
    renderSeats(state)
    renderRole('actor1', state)
    renderRole('actor2', state)
    renderRole('observer', state)
    applyStarted(!!state.is_started)
    if (state.is_started) {
      showPlay(state)
    }
    const currentId = state.scenario_id == null ? '' : String(state.scenario_id)
    page.querySelectorAll('[data-scenario-id]').forEach((card) => {
      const current = card.dataset.scenarioId === currentId
      card.classList.toggle('is-current', current)
      if (current) {
        card.setAttribute('aria-current', 'true')
      } else {
        card.removeAttribute('aria-current')
      }
    })
  }

  const hasDoc = (doc) => Boolean(doc && Array.isArray(doc.content) && doc.content.length)

  const showPlay = (state) => {
    for (const name of ['target1', 'target2', 'context1', 'context2']) {
      const field = page.querySelector(`[data-play-field="${name}"]`)
      const text = page.querySelector(`[data-slot="${name}"]`)
      if (field) {
        field.hidden = !(text && text.textContent.trim())
      }
    }
    const mine = (state.players || []).find((player) => player.nickname === me && !player.left)
    const role = mine ? mine.role : ''
    const actor = role === 'actor1' || role === 'actor2'
    const briefs = page.querySelector('[data-play-briefs]')
    if (briefs) {
      briefs.classList.toggle('is-single', actor)
    }
    page.querySelectorAll('[data-play-role]').forEach((card) => {
      card.hidden = actor && card.dataset.playRole !== role
    })
    for (const name of ['doc1', 'doc2']) {
      const filled = hasDoc(state[name])
      const wrap = page.querySelector(`[data-play-doc="${name}"]`)
      if (wrap) {
        wrap.hidden = !filled
      }
      const slot = page.querySelector(`[data-editor="${name}"]`)
      if (!slot) {
        continue
      }
      const editor = playEditors.get(name)
      if (editor) {
        setDocument(editor, state[name])
      } else {
        playEditors.set(name, createDocumentEditor({ element: slot, content: state[name], editable: false }))
      }
    }
    page.querySelectorAll('[data-play-role]').forEach((card) => {
      const doc = card.dataset.playRole === 'actor2' ? 'doc2' : 'doc1'
      const empty = card.querySelector('.play-role__empty')
      const visibleField = card.querySelector('.play-role__field:not([hidden])')
      if (empty) {
        empty.hidden = Boolean(visibleField) || hasDoc(state[doc])
      }
    })
  }

  const applyStarted = (started) => {
    const wait = page.querySelector('[data-lobby-wait]')
    const play = page.querySelector('[data-lobby-play]')
    if (wait) {
      wait.hidden = started
    }
    if (play) {
      play.hidden = !started
    }
    setText('stage', started ? 'Ролевка' : 'Лобби')
    page.classList.toggle('is-playing', started)
    if (startButton) {
      startButton.disabled = started
    }
    if (scenarioButton) {
      scenarioButton.hidden = started
    }
    const finishForm = page.querySelector('[data-lobby-finish]')
    if (finishForm) {
      finishForm.hidden = !started
    }
    if (started) {
      closeScenario()
    }
  }

  const readErrors = (html) => {
    const doc = new DOMParser().parseFromString(html, 'text/html')
    if (doc.title === 'Ошибка') {
      const message = doc.querySelector('main p')
      return message ? [message.textContent.trim()] : []
    }
    return [...doc.querySelectorAll('.session-lobby__error li')]
      .map((node) => node.textContent.trim())
      .filter(Boolean)
  }

  page.addEventListener('submit', (event) => {
    const form = event.target
    if (!(form instanceof HTMLFormElement) || form.classList.contains('session-lobby__leave')) {
      return
    }
    event.preventDefault()
    if (form.dataset.pending === '1') {
      return
    }
    form.dataset.pending = '1'
    const picking = form.hasAttribute('data-lobby-pick')
    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      redirect: 'manual',
    }).then(async (response) => {
      if (
        response.type === 'opaqueredirect'
        || (response.status >= 300 && response.status < 400)
        || response.ok
      ) {
        showError([])
        if (picking) {
          closeScenario()
        }
        if (startButton && form.contains(startButton)) {
          applyStarted(true)
        }
        if (form.hasAttribute('data-lobby-finish')) {
          applyStarted(false)
        }
        return
      }
      const messages = readErrors(await response.text())
      showError(messages.length ? messages : ['Не получилось'])
    }).catch(() => {
      showError(['Нет соединения'])
    }).finally(() => {
      delete form.dataset.pending
    })
  })

  const copy = page.querySelector('[data-lobby-copy]')
  let copiedTimer = 0
  copy?.addEventListener('click', () => {
    const pending = navigator.clipboard?.writeText(page.dataset.roomCode || '')
    if (!pending) return
    pending.then(() => {
      copy.classList.add('is-copied')
      window.clearTimeout(copiedTimer)
      copiedTimer = window.setTimeout(() => copy.classList.remove('is-copied'), 1200)
    }).catch(() => {})
  })

  const socket = io('/room', { auth: { code: page.dataset.roomCode } })
  socket.on('state', render)
  socket.on('closed', () => setText('status', 'комната закрыта'))
  socket.on('disconnect', () => setText('status', 'нет соединения, переподключение…'))
  // active === false: сервер отказал (не участник), клиент сам больше не переподключается
  socket.on('connect_error', () => setText(
    'status', socket.active ? 'нет соединения, переподключение…' : 'нет доступа к комнате',
  ))
}
