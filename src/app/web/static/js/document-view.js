// Документы сценария только для чтения: JSON из TipTap лежит в data-document-view.
import { createDocumentEditor } from './vendor/tiptap.bundle.js'

for (const node of document.querySelectorAll('[data-document-view]')) {
  createDocumentEditor({ element: node, content: JSON.parse(node.dataset.documentView), editable: false })
}
