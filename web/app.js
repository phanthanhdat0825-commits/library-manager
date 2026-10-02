const catalogList = document.querySelector('#catalog-list');
const catalogMessage = document.querySelector('#catalog-message');
const searchInput = document.querySelector('#search-input');
const selectedList = document.querySelector('#selected-list');
const selectedCount = document.querySelector('#selected-count');
const requestForm = document.querySelector('#request-form');
const formMessage = document.querySelector('#form-message');
const trackingResult = document.querySelector('#tracking-result');
const selectedBooks = new Map();
let allBooks = [];
let searchTimer;

const statusNames = {
  pending: 'Đang chờ thư viện xem xét',
  approved: 'Đã được chấp thuận',
  rejected: 'Không được chấp thuận',
};

function setFeedback(element, message, isError = true) {
  element.textContent = message;
  element.classList.toggle('success', !isError && Boolean(message));
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Không thể kết nối dịch vụ thư viện.');
  return data;
}

function renderCatalog(books) {
  catalogList.replaceChildren();
  document.querySelector('#catalog-count').textContent = `${books.length} tài liệu`;
  if (!books.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = 'Không tìm thấy tài liệu phù hợp.';
    catalogList.append(empty);
    return;
  }

  books.forEach((book, index) => {
    const row = document.createElement('article');
    row.className = 'book-row';
    row.style.animationDelay = `${Math.min(index, 8) * 25}ms`;

    const details = document.createElement('div');
    const title = document.createElement('h3');
    title.className = 'book-title';
    title.textContent = book.title;
    const meta = document.createElement('div');
    meta.className = 'book-meta';
    const code = document.createElement('span');
    code.className = 'book-code';
    code.textContent = book.book_code;
    meta.append(code);
    [book.author, book.category, book.publisher].filter(Boolean).forEach((value) => {
      const span = document.createElement('span');
      span.textContent = value;
      meta.append(span);
    });
    details.append(title, meta);

    const stock = document.createElement('div');
    stock.className = 'book-stock';
    const stockText = document.createElement('span');
    stockText.className = 'stock-label';
    const available = Number(book.available || 0);
    const stockCount = document.createElement('strong');
    stockCount.textContent = String(available);
    stockText.append(stockCount, document.createTextNode(' còn'));
    const add = document.createElement('button');
    add.type = 'button';
    add.className = 'add-button';
    add.setAttribute('aria-label', `Thêm ${book.title} vào yêu cầu`);
    add.title = 'Thêm vào phiếu yêu cầu';
    add.textContent = '+';
    add.disabled = available < 1;
    add.addEventListener('click', () => addBook(book));
    stock.append(stockText, add);
    row.append(details, stock);
    catalogList.append(row);
  });
}

async function loadCatalog(query = '') {
  setFeedback(catalogMessage, '');
  try {
    const data = await api(`/api/catalog?q=${encodeURIComponent(query)}`);
    allBooks = data.books;
    renderCatalog(allBooks);
    const syncedAt = allBooks[0]?.synced_at;
    const label = syncedAt ? `Danh mục cập nhật ${new Date(syncedAt).toLocaleString('vi-VN')}` : 'Danh mục chưa được đồng bộ';
    document.querySelector('#sync-label').textContent = label;
    document.querySelector('#footer-sync').textContent = label;
  } catch (error) {
    setFeedback(catalogMessage, error.message);
    document.querySelector('#sync-label').textContent = 'Không kết nối được thư viện';
  }
}

function addBook(book) {
  const existing = selectedBooks.get(book.book_code);
  if (existing) existing.quantity = Math.min(existing.quantity + 1, Number(book.available));
  else selectedBooks.set(book.book_code, { ...book, quantity: 1 });
  renderSelected();
}

function renderSelected() {
  selectedList.replaceChildren();
  selectedCount.textContent = String(selectedBooks.size);
  if (!selectedBooks.size) {
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = 'Chưa chọn tài liệu';
    selectedList.append(empty);
    return;
  }
  selectedBooks.forEach((book, code) => {
    const row = document.createElement('div');
    row.className = 'selected-item';
    const title = document.createElement('strong');
    title.textContent = `${book.title} (${code})`;
    const quantity = document.createElement('input');
    quantity.type = 'number';
    quantity.min = '1';
    quantity.max = String(book.available);
    quantity.value = String(book.quantity);
    quantity.setAttribute('aria-label', `Số lượng ${book.title}`);
    quantity.addEventListener('change', () => {
      book.quantity = Math.max(1, Math.min(Number(quantity.value) || 1, Number(book.available)));
      quantity.value = String(book.quantity);
    });
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'remove-item';
    remove.setAttribute('aria-label', `Bỏ ${book.title}`);
    remove.title = 'Bỏ khỏi phiếu';
    remove.textContent = '×';
    remove.addEventListener('click', () => {
      selectedBooks.delete(code);
      renderSelected();
    });
    row.append(title, quantity, remove);
    selectedList.append(row);
  });
}

requestForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  setFeedback(formMessage, '');
  if (!selectedBooks.size) {
    setFeedback(formMessage, 'Hãy chọn ít nhất một tài liệu.');
    return;
  }
  const form = new FormData(requestForm);
  const contact = String(form.get('contact') || '').trim();
  const payload = {
    reader_code: String(form.get('reader_code')).trim(),
    name: String(form.get('name')).trim(),
    requester_type: form.get('requester_type'),
    class_name: String(form.get('class_name') || '').trim(),
    email: contact.includes('@') ? contact : '',
    phone: contact.includes('@') ? '' : contact,
    note: String(form.get('note') || '').trim(),
    items: [...selectedBooks.values()].map((book) => ({ book_code: book.book_code, quantity: book.quantity })),
  };

  const submitButton = requestForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  try {
    const result = await api('/api/requests', { method: 'POST', body: JSON.stringify(payload) });
    trackingResult.replaceChildren();
    const heading = document.createElement('strong');
    heading.textContent = 'Đã gửi yêu cầu';
    const text = document.createElement('span');
    text.textContent = `Mã yêu cầu ${result.request_id} · Mã tra cứu ${result.tracking_token}. Hãy lưu lại để xem kết quả.`;
    trackingResult.append(heading, text);
    trackingResult.hidden = false;
    document.querySelector('#tracking-form [name="request_id"]').value = result.request_id;
    document.querySelector('#tracking-form [name="token"]').value = result.tracking_token;
    requestForm.reset();
    selectedBooks.clear();
    renderSelected();
    setFeedback(formMessage, 'Phiếu đã được chuyển đến thư viện.', false);
  } catch (error) {
    setFeedback(formMessage, error.message);
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelector('#tracking-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const id = String(form.get('request_id')).trim();
  const token = String(form.get('token')).trim();
  try {
    const result = await api('/api/requests/status', {
      method: 'POST',
      body: JSON.stringify({ request_id: Number(id), token }),
    });
    const status = statusNames[result.status] || result.status;
    const reason = result.decision_reason ? ` · Lý do: ${result.decision_reason}` : '';
    setFeedback(document.querySelector('#tracking-message'), `${status}${reason}`, false);
  } catch (error) {
    setFeedback(document.querySelector('#tracking-message'), error.message);
  }
});

searchInput.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadCatalog(searchInput.value.trim()), 220);
});
document.addEventListener('keydown', (event) => {
  if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
    event.preventDefault();
    searchInput.focus();
  }
});

renderSelected();
loadCatalog();
