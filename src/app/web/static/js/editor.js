// Редактор сценария: черновик живёт в service, страница синхронизирует изменения по сокету.
// Данные пользователя выводятся только через value, textContent и TipTap — никакого innerHTML.
import { createDocumentEditor, isAllowedLink, setDocument } from './vendor/tiptap.bundle.js'

const SYNC_DELAY = 1000
const ACK_TIMEOUT = 10000

const page = document.querySelector('[data-scenario-id]')
if (page) {
  start(page)
}

function start(page) {
  const scenarioId = Number(page.dataset.scenarioId)
  const statusNode = page.querySelector('[data-status]')
  const setStatus = (text) => {
    statusNode.textContent = text
  }

  const fields = new Map([...page.querySelectorAll('[data-field]')].map((node) => [node.dataset.field, node]))
  const editors = new Map()

  // dirty — изменено и ещё не отправлено, pending — отправлено, ответа пока нет
  const dirty = new Set()
  const pending = new Set()
  const isLocal = (name) => dirty.has(name) || pending.has(name)

  let revision = null
  let timer = null
  let queue = Promise.resolve()

  const socket = io('/editor', { auth: { scenario_id: scenarioId } })

  const valueOf = (name) => (editors.has(name) ? editors.get(name).getJSON() : fields.get(name).value)

  const markDirty = (name) => {
    dirty.add(name)
    setStatus('есть непереданные изменения')
    clearTimeout(timer)
    timer = setTimeout(flush, SYNC_DELAY)
  }

  const sendDirty = () => {
    if (revision === null || dirty.size === 0) {
      return undefined
    }
    const names = [...dirty]
    dirty.clear()
    names.forEach((name) => pending.add(name))
    const patch = Object.fromEntries(names.map((name) => [name, valueOf(name)]))

    return new Promise((resolve) => {
      socket.timeout(ACK_TIMEOUT).emit('update', { scenario_id: scenarioId, revision, patch }, (timeoutError, ack) => {
        names.forEach((name) => pending.delete(name))
        if (!timeoutError && ack?.ok) {
          revision = ack.revision
          setStatus(dirty.size ? 'есть непереданные изменения' : 'изменения переданы')
        } else {
          // неотправленное остаётся у пользователя и уйдёт со следующей правкой
          names.forEach((name) => dirty.add(name))
          setStatus(timeoutError ? 'сервер не ответил' : ack?.error ?? 'ошибка')
        }
        resolve()
      })
    })
  }

  // обновления уходят строго по очереди: каждое опирается на revision предыдущего
  const flush = () => {
    clearTimeout(timer)
    queue = queue.then(sendDirty)
    return queue
  }

  const applyState = (state) => {
    revision = state.revision
    for (const [name, node] of fields) {
      if (!isLocal(name)) {
        node.value = state[name] ?? ''
      }
    }
    for (const [name, editor] of editors) {
      if (!isLocal(name)) {
        setDocument(editor, state[name])
      }
    }
  }

  const toolbars = []

  const enable = () => {
    fields.forEach((node) => {
      node.disabled = false
    })
    // false: включение редактора не должно выглядеть как правка документа
    editors.forEach((editor) => editor.setEditable(true, false))
    toolbars.forEach((refresh) => refresh())
  }

  // поля
  for (const [name, node] of fields) {
    node.disabled = true
    node.addEventListener('input', () => markDirty(name))
  }

  // документы
  for (const container of page.querySelectorAll('[data-document]')) {
    const name = container.dataset.document
    const editor = createDocumentEditor({
      element: container.querySelector('[data-editor]'),
      editable: false,
      onUpdate: () => markDirty(name),
    })
    editors.set(name, editor)
    toolbars.push(bindToolbar(container.querySelector('[data-toolbar]'), editor, setStatus))
  }

  page.querySelector('[data-save]').addEventListener('click', () => {
    setStatus('сохранение…')
    flush().then(() => {
      socket.timeout(ACK_TIMEOUT).emit('save', { scenario_id: scenarioId }, (timeoutError, ack) => {
        if (timeoutError) {
          setStatus('сервер не ответил')
        } else {
          setStatus(ack?.ok ? 'сохранено' : ack?.error ?? 'ошибка')
        }
      })
    })
  })

  // ушёл со страницы — передать последнее; браузер предупредит, если что-то не дошло
  window.addEventListener('beforeunload', (event) => {
    if (dirty.size || pending.size) {
      flush()
      event.preventDefault()
    }
  })

  let ready = false
  socket.on('state', (state) => {
    applyState(state)
    if (!ready) {
      ready = true
      enable()
      setStatus('готово')
    }
  })
  socket.on('disconnect', () => setStatus('нет соединения, переподключение…'))
  // active === false: сервер отказал (нет доступа), клиент сам больше не переподключается
  socket.on('connect_error', () => setStatus(
    socket.active ? 'нет соединения, переподключение…' : 'нет доступа к сценарию',
  ))
}

const COMMANDS = {
  bold: { run: (chain) => chain.toggleBold(), isActive: (editor) => editor.isActive('bold') },
  italic: { run: (chain) => chain.toggleItalic(), isActive: (editor) => editor.isActive('italic') },
  strike: { run: (chain) => chain.toggleStrike(), isActive: (editor) => editor.isActive('strike') },
  underline: { run: (chain) => chain.toggleUnderline(), isActive: (editor) => editor.isActive('underline') },
  orderedList: { run: (chain) => chain.toggleOrderedList(), isActive: (editor) => editor.isActive('orderedList') },
  bulletList: { run: (chain) => chain.toggleBulletList(), isActive: (editor) => editor.isActive('bulletList') },
  heading: {
    run: (chain) => chain.toggleHeading({ level: 1 }),
    isActive: (editor) => editor.isActive('heading', { level: 1 }),
  },
}

function toggleLink(editor, setStatus) {
  if (editor.isActive('link')) {
    editor.chain().focus().extendMarkRange('link').unsetLink().run()
    return
  }
  const input = window.prompt('Адрес ссылки (http:// или https://)')
  if (!input) {
    return
  }
  const href = /^[a-z][a-z0-9+.-]*:/i.test(input.trim()) ? input.trim() : `https://${input.trim()}`
  if (!isAllowedLink(href)) {
    setStatus('ссылка должна начинаться с http:// или https://')
    return
  }
  editor.chain().focus().extendMarkRange('link').setLink({ href }).run()
}

function bindToolbar(toolbar, editor, setStatus) {
  const buttons = [...toolbar.querySelectorAll('[data-command]')]

  for (const button of buttons) {
    const name = button.dataset.command
    button.addEventListener('click', () => {
      if (name === 'link') {
        toggleLink(editor, setStatus)
      } else {
        COMMANDS[name].run(editor.chain().focus()).run()
      }
    })
  }

  // без CSS нажатое состояние видно только в aria-pressed
  const refresh = () => {
    for (const button of buttons) {
      const name = button.dataset.command
      const active = name === 'link' ? editor.isActive('link') : COMMANDS[name].isActive(editor)
      button.setAttribute('aria-pressed', String(active))
      button.disabled = !editor.isEditable
    }
  }
  editor.on('transaction', refresh)
  refresh()
  return refresh
}
