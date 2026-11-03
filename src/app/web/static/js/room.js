// Страница комнаты: подключиться к сокету и рисовать присланное состояние.
// Текст — только через textContent, документы — через TipTap только для чтения; никакого innerHTML.
import { createDocumentEditor, setDocument } from './vendor/tiptap.bundle.js'

const page = document.querySelector('[data-room-code]')
if (page) {
  start(page)
}

function start(page) {
  const slots = (name) => page.querySelectorAll(`[data-slot="${name}"]`)

  const setText = (name, value) => {
    slots(name).forEach((node) => {
      node.textContent = value ?? ''
    })
  }

  const viewers = new Map()
  const setDocumentSlot = (name, doc) => {
    slots(name).forEach((node) => {
      const viewer = viewers.get(node)
      if (viewer) {
        setDocument(viewer, doc)
      } else {
        viewers.set(node, createDocumentEditor({ element: node, content: doc, editable: false }))
      }
    })
  }

  const roleLabel = (role, state) => {
    switch (role) {
      case 'actor1':
        return state.actor1
      case 'actor2':
        return state.actor2
      case 'observer':
        return 'Наблюдатель'
      default:
        return 'без роли'
    }
  }

  const renderPlayers = (state) => state.players.map((player) => {
    let text = `${player.nickname} — ${roleLabel(player.role, state)}`
    if (player.is_owner) {
      text += ' (владелец)'
    }
    if (player.left) {
      text += ' (вышел)'
    }
    const item = document.createElement('li')
    item.textContent = text
    return item
  })

  const render = (state) => {
    setText('status', state.is_started ? 'идёт игра' : 'ожидание')
    setText('title', state.title)
    setText('actor1', state.actor1)
    setText('actor2', state.actor2)
    setText('target1', state.target1 || '—')
    setText('target2', state.target2 || '—')
    setText('context1', state.context1 || '—')
    setText('context2', state.context2 || '—')
    slots('players').forEach((node) => node.replaceChildren(...renderPlayers(state)))
    setDocumentSlot('doc1', state.doc1)
    setDocumentSlot('doc2', state.doc2)
  }

  const socket = io('/room', { auth: { code: page.dataset.roomCode } })
  socket.on('state', render)
  socket.on('closed', () => setText('status', 'комната закрыта'))
  socket.on('disconnect', () => setText('status', 'нет соединения, переподключение…'))
  // active === false: сервер отказал (не участник), клиент сам больше не переподключается
  socket.on('connect_error', () => setText(
    'status', socket.active ? 'нет соединения, переподключение…' : 'нет доступа к комнате',
  ))
}
