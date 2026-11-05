const popups = [...document.querySelectorAll('[data-profile-popup]')]

const closePopups = () => {
  popups.forEach((popup) => {
    popup.hidden = true
  })
  document.body.classList.remove('profile-popup-open')
}

const openPopup = (name) => {
  const popup = popups.find((node) => node.dataset.profilePopup === name)
  if (!popup) {
    return
  }
  closePopups()
  popup.hidden = false
  document.body.classList.add('profile-popup-open')
  popup.querySelector('input')?.focus()
}

document.querySelectorAll('[data-profile-open]').forEach((button) => {
  button.addEventListener('click', () => openPopup(button.dataset.profileOpen))
})

popups.forEach((popup) => {
  popup.querySelectorAll('[data-profile-close]').forEach((node) => {
    node.addEventListener('click', closePopups)
  })
})

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    closePopups()
  }
})

const opened = popups.find((popup) => !popup.hidden)
if (opened) {
  document.body.classList.add('profile-popup-open')
  opened.querySelector('input')?.focus()
}
