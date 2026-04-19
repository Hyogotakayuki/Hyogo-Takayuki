/* ===== STATE ===== */
let allAssets = [];
let allIncome = [];
let allExpenses = [];
let allTransactions = [];
let currentAssetFilter = 'all';
let currentExpenseFilter = 'all';
let currentTxFilter = 'all';
let currentTxYear = new Date().getFullYear();
let currentTxMonth = new Date().getMonth() + 1;
let currentTxType = 'income';
let pendingDelete = null;
let assetsChart = null;
let expensesChart = null;

const CATEGORY_LABELS = { bank: '銀行', stocks: '株式', insurance: '保険', pension: '障害年金', savings: '積立', self_defense: '自己防衛費' };
const CATEGORY_ICONS = { bank: '🏦', stocks: '📈', insurance: '🛡️', pension: '👴', savings: '💹', self_defense: '🔒' };
const FREQ_LABELS = { monthly: '毎月', bimonthly: '隔月', quarterly: '四半期', annual: '年1回' };
const FREQ_MULT = { monthly: 12, bimonthly: 6, quarterly: 4, annual: 1 };
const EXPENSE_LABELS = { subscription: 'サブスク', food: '食費', utilities: '光熱費', socializing: '交際費', hygiene: '衛生費', stress_relief: '娯楽費', enrichment: '教養費', other: 'その他' };
const EXPENSE_ICONS = { subscription: '📱', food: '🍽️', utilities: '💡', socializing: '🥂', hygiene: '🧴', stress_relief: '🎮', enrichment: '📚', other: '📝' };

const TX_INCOME_CATEGORIES = { salary: '給与', business: '事業収入', investment: '投資収益', pension: '年金・障害年金', other_income: 'その他収入' };
const TX_EXPENSE_CATEGORIES = { food: '食費', utilities: '光熱費', subscription: 'サブスク', socializing: '交際費', hygiene: '衛生費', stress_relief: '娯楽費', enrichment: '教養費', medical: '医療費', transport: '交通費', clothing: '被服費', other: 'その他' };
const TX_INCOME_ICONS = { salary: '💼', business: '🏢', investment: '📈', pension: '👴', other_income: '💴' };
const TX_EXPENSE_ICONS = { food: '🍽️', utilities: '💡', subscription: '📱', socializing: '🥂', hygiene: '🧴', stress_relief: '🎮', enrichment: '📚', medical: '🏥', transport: '🚃', clothing: '👔', other: '📝' };

/* ===== FORMAT ===== */
function formatYen(n) {
  return '¥' + Math.round(n).toLocaleString('ja-JP');
}

/* ===== API ===== */
async function api(method, url, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'エラーが発生しました');
  return data;
}

/* ===== AUTH ===== */
async function checkAuth() {
  const data = await api('GET', '/api/auth/me');
  if (data.loggedIn) {
    showApp(data.username);
    loadAll();
  } else {
    showAuthPage();
  }
}

function showApp(username) {
  document.getElementById('auth-page').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  document.getElementById('sidebar-username').textContent = username;
}

function showAuthPage() {
  document.getElementById('app').classList.add('hidden');
  document.getElementById('auth-page').classList.remove('hidden');
}

function switchAuthTab(tab) {
  const isLogin = tab === 'login';
  document.getElementById('login-form').classList.toggle('hidden', !isLogin);
  document.getElementById('register-form').classList.toggle('hidden', isLogin);
  document.querySelectorAll('.tab-btn').forEach((b, i) => {
    b.classList.toggle('active', isLogin ? i === 0 : i === 1);
  });
}

async function handleLogin(e) {
  e.preventDefault();
  const errorEl = document.getElementById('login-error');
  errorEl.textContent = '';
  try {
    const data = await api('POST', '/api/auth/login', {
      email: document.getElementById('login-email').value,
      password: document.getElementById('login-password').value
    });
    showApp(data.username);
    loadAll();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const errorEl = document.getElementById('register-error');
  errorEl.textContent = '';
  try {
    const data = await api('POST', '/api/auth/register', {
      username: document.getElementById('reg-username').value,
      email: document.getElementById('reg-email').value,
      password: document.getElementById('reg-password').value
    });
    showApp(data.username);
    loadAll();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

async function handleLogout() {
  await api('POST', '/api/auth/logout');
  allAssets = []; allIncome = []; allExpenses = [];
  showAuthPage();
}

/* ===== NAVIGATION ===== */
function showPage(name, linkEl) {
  document.querySelectorAll('.page').forEach(p => {
    p.classList.remove('active');
    p.classList.add('hidden');
  });
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const page = document.getElementById('page-' + name);
  page.classList.remove('hidden');
  page.classList.add('active');
  if (linkEl) linkEl.classList.add('active');
  if (name === 'dashboard') loadDashboard();
  if (name === 'transactions') initTransactionsPage();
}

/* ===== LOAD ALL DATA ===== */
async function loadAll() {
  await Promise.all([loadAssets(), loadIncome(), loadExpenses()]);
  loadDashboard();
}

function initTransactionsPage() {
  updateTxMonthLabel();
  loadTransactions();
}

/* ===== DASHBOARD ===== */
async function loadDashboard() {
  try {
    const d = await api('GET', '/api/dashboard');
    document.getElementById('dash-total-assets').textContent = formatYen(d.totalAssets);
    document.getElementById('dash-annual-income').textContent = formatYen(d.annualIncome);
    document.getElementById('dash-monthly-expenses').textContent = formatYen(d.monthlyExpenses);

    const scoreEl = document.getElementById('dash-health-score');
    const labelEl = document.getElementById('dash-health-label');
    const healthCard = document.querySelector('.health-card');

    if (d.healthScore !== null) {
      scoreEl.textContent = d.healthScore.toFixed(2) + '倍';
    } else {
      scoreEl.textContent = '--';
    }
    labelEl.textContent = d.healthLabel;
    labelEl.style.color = d.healthColor;
    healthCard.style.borderTopColor = d.healthColor;

    // Charts
    const catMap = { bank: '銀行', stocks: '株式', insurance: '保険', pension: '障害年金', savings: '積立', self_defense: '自己防衛費' };
    const catColors = ['#0f3460', '#e94560', '#4caf50', '#ff9800', '#00bcd4', '#9c27b0'];
    const expCatMap = { subscription: 'サブスク', food: '食費', utilities: '光熱費', socializing: '交際費', hygiene: '衛生費', stress_relief: '娯楽費', enrichment: '教養費', other: 'その他' };
    const expColors = ['#9c27b0', '#e91e63', '#ff9800', '#00bcd4', '#4caf50', '#ff5722', '#3f51b5', '#795548'];

    renderPieChart('assets-chart', assetsChart,
      d.assetsByCategory.map(a => catMap[a.category] || a.category),
      d.assetsByCategory.map(a => a.total),
      catColors,
      (c) => { assetsChart = c; }
    );

    renderPieChart('expenses-chart', expensesChart,
      d.expensesByCategory.map(e => expCatMap[e.category] || e.category),
      d.expensesByCategory.map(e => e.total),
      expColors,
      (c) => { expensesChart = c; }
    );
  } catch (e) {
    console.error('Dashboard load error:', e);
  }
}

function renderPieChart(canvasId, existingChart, labels, data, colors, setChart) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  if (existingChart) existingChart.destroy();
  if (!data.length || data.every(v => v === 0)) {
    const chart = new Chart(ctx, {
      type: 'doughnut',
      data: { labels: ['データなし'], datasets: [{ data: [1], backgroundColor: ['#e0e0e0'] }] },
      options: { plugins: { legend: { display: false } }, cutout: '65%' }
    });
    setChart(chart);
    return;
  }
  const chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.slice(0, data.length),
        borderWidth: 2,
        borderColor: '#fff'
      }]
    },
    options: {
      cutout: '65%',
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 12 }, padding: 12 } },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${formatYen(ctx.raw)}`
          }
        }
      }
    }
  });
  setChart(chart);
}

/* ===== ASSETS ===== */
async function loadAssets() {
  try {
    allAssets = await api('GET', '/api/assets');
    renderAssets();
  } catch (e) { console.error(e); }
}

function filterAssets(cat, el) {
  currentAssetFilter = cat;
  document.querySelectorAll('#page-assets .cat-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  renderAssets();
}

function renderAssets() {
  const list = document.getElementById('assets-list');
  const filtered = currentAssetFilter === 'all' ? allAssets : allAssets.filter(a => a.category === currentAssetFilter);
  const total = filtered.reduce((s, a) => s + a.amount, 0);
  document.getElementById('assets-total').textContent = formatYen(total);

  if (!filtered.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">🏦</div><p>資産がありません。「＋ 資産を追加」から登録してください。</p></div>`;
    return;
  }

  list.innerHTML = filtered.map(a => `
    <div class="item-card">
      <div class="item-icon">${CATEGORY_ICONS[a.category] || '💰'}</div>
      <div class="item-info">
        <div class="item-name">${escHtml(a.name)}</div>
        <div class="item-meta">${CATEGORY_LABELS[a.category] || a.category}${a.notes ? ' · ' + escHtml(a.notes) : ''}</div>
      </div>
      <div class="item-amount">${formatYen(a.amount)}</div>
      <div class="item-actions">
        <button class="btn btn-ghost btn-icon" onclick="openEditAsset(${a.id})">編集</button>
        <button class="btn btn-danger btn-icon" onclick="openDelete('asset', ${a.id})">削除</button>
      </div>
    </div>
  `).join('');
}

function openEditAsset(id) {
  const a = allAssets.find(x => x.id === id);
  if (!a) return;
  document.getElementById('asset-modal-title').textContent = '資産を編集';
  document.getElementById('asset-id').value = a.id;
  document.getElementById('asset-category').value = a.category;
  document.getElementById('asset-name').value = a.name;
  document.getElementById('asset-amount').value = a.amount;
  document.getElementById('asset-notes').value = a.notes || '';
  document.getElementById('asset-error').textContent = '';
  openModal('asset-modal');
}

async function handleAssetSubmit(e) {
  e.preventDefault();
  const id = document.getElementById('asset-id').value;
  const body = {
    category: document.getElementById('asset-category').value,
    name: document.getElementById('asset-name').value,
    amount: document.getElementById('asset-amount').value,
    notes: document.getElementById('asset-notes').value
  };
  const errorEl = document.getElementById('asset-error');
  try {
    if (id) {
      await api('PUT', `/api/assets/${id}`, body);
    } else {
      await api('POST', '/api/assets', body);
    }
    closeModal('asset-modal');
    await loadAssets();
    loadDashboard();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

/* ===== INCOME ===== */
async function loadIncome() {
  try {
    allIncome = await api('GET', '/api/income');
    renderIncome();
  } catch (e) { console.error(e); }
}

function renderIncome() {
  const list = document.getElementById('income-list');
  const totalAnnual = allIncome.reduce((s, i) => s + i.annual, 0);
  document.getElementById('income-total').textContent = formatYen(totalAnnual);

  if (!allIncome.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">💰</div><p>収入源がありません。「＋ 収入源を追加」から登録してください。</p></div>`;
    return;
  }

  list.innerHTML = allIncome.map(i => `
    <div class="item-card">
      <div class="item-icon">💴</div>
      <div class="item-info">
        <div class="item-name">${escHtml(i.name)}</div>
        <div class="item-meta">${FREQ_LABELS[i.frequency]} ${formatYen(i.amount)}${i.notes ? ' · ' + escHtml(i.notes) : ''}</div>
      </div>
      <div class="item-amount">${formatYen(i.annual)}<span style="font-size:0.75rem;color:#888">/年</span></div>
      <div class="item-actions">
        <button class="btn btn-ghost btn-icon" onclick="openEditIncome(${i.id})">編集</button>
        <button class="btn btn-danger btn-icon" onclick="openDelete('income', ${i.id})">削除</button>
      </div>
    </div>
  `).join('');
}

function openEditIncome(id) {
  const i = allIncome.find(x => x.id === id);
  if (!i) return;
  document.getElementById('income-modal-title').textContent = '収入源を編集';
  document.getElementById('income-id').value = i.id;
  document.getElementById('income-name').value = i.name;
  document.getElementById('income-amount').value = i.amount;
  document.getElementById('income-frequency').value = i.frequency;
  document.getElementById('income-notes').value = i.notes || '';
  document.getElementById('income-error').textContent = '';
  updateAnnualPreview();
  openModal('income-modal');
}

function updateAnnualPreview() {
  const amount = parseFloat(document.getElementById('income-amount').value) || 0;
  const freq = document.getElementById('income-frequency').value;
  const previewEl = document.getElementById('income-annual-preview');
  if (amount > 0 && freq) {
    const annual = amount * (FREQ_MULT[freq] || 0);
    previewEl.textContent = `年収換算: ${formatYen(annual)}`;
    previewEl.classList.remove('hidden');
  } else {
    previewEl.classList.add('hidden');
  }
}

async function handleIncomeSubmit(e) {
  e.preventDefault();
  const id = document.getElementById('income-id').value;
  const body = {
    name: document.getElementById('income-name').value,
    amount: document.getElementById('income-amount').value,
    frequency: document.getElementById('income-frequency').value,
    notes: document.getElementById('income-notes').value
  };
  const errorEl = document.getElementById('income-error');
  try {
    if (id) {
      await api('PUT', `/api/income/${id}`, body);
    } else {
      await api('POST', '/api/income', body);
    }
    closeModal('income-modal');
    await loadIncome();
    loadDashboard();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

/* ===== EXPENSES ===== */
async function loadExpenses() {
  try {
    allExpenses = await api('GET', '/api/expenses');
    renderExpenses();
  } catch (e) { console.error(e); }
}

function filterExpenses(cat, el) {
  currentExpenseFilter = cat;
  document.querySelectorAll('#page-expenses .cat-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  renderExpenses();
}

function renderExpenses() {
  const list = document.getElementById('expenses-list');
  const filtered = currentExpenseFilter === 'all' ? allExpenses : allExpenses.filter(e => e.category === currentExpenseFilter);
  const total = filtered.reduce((s, e) => s + e.amount, 0);
  document.getElementById('expenses-total').textContent = formatYen(total);

  if (!filtered.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">💳</div><p>費用がありません。「＋ 費用を追加」から登録してください。</p></div>`;
    return;
  }

  list.innerHTML = filtered.map(e => `
    <div class="item-card">
      <div class="item-icon">${EXPENSE_ICONS[e.category] || '💳'}</div>
      <div class="item-info">
        <div class="item-name">${escHtml(e.name)}</div>
        <div class="item-meta">${EXPENSE_LABELS[e.category] || e.category}${e.notes ? ' · ' + escHtml(e.notes) : ''}</div>
      </div>
      <div class="item-amount">${formatYen(e.amount)}<span style="font-size:0.75rem;color:#888">/月</span></div>
      <div class="item-actions">
        <button class="btn btn-ghost btn-icon" onclick="openEditExpense(${e.id})">編集</button>
        <button class="btn btn-danger btn-icon" onclick="openDelete('expense', ${e.id})">削除</button>
      </div>
    </div>
  `).join('');
}

function openEditExpense(id) {
  const e = allExpenses.find(x => x.id === id);
  if (!e) return;
  document.getElementById('expense-modal-title').textContent = '費用を編集';
  document.getElementById('expense-id').value = e.id;
  document.getElementById('expense-category').value = e.category;
  document.getElementById('expense-name').value = e.name;
  document.getElementById('expense-amount').value = e.amount;
  document.getElementById('expense-notes').value = e.notes || '';
  document.getElementById('expense-error').textContent = '';
  openModal('expense-modal');
}

async function handleExpenseSubmit(e) {
  e.preventDefault();
  const id = document.getElementById('expense-id').value;
  const body = {
    category: document.getElementById('expense-category').value,
    name: document.getElementById('expense-name').value,
    amount: document.getElementById('expense-amount').value,
    notes: document.getElementById('expense-notes').value
  };
  const errorEl = document.getElementById('expense-error');
  try {
    if (id) {
      await api('PUT', `/api/expenses/${id}`, body);
    } else {
      await api('POST', '/api/expenses', body);
    }
    closeModal('expense-modal');
    await loadExpenses();
    loadDashboard();
  } catch (err) {
    errorEl.textContent = err.message;
  }
}

/* ===== DELETE ===== */
function openDelete(type, id) {
  pendingDelete = { type, id };
  openModal('delete-modal');
}

async function confirmDelete() {
  if (!pendingDelete) return;
  const { type, id } = pendingDelete;
  const urlMap = { asset: '/api/assets', income: '/api/income', expense: '/api/expenses', transaction: '/api/transactions' };
  try {
    await api('DELETE', `${urlMap[type]}/${id}`);
    closeModal('delete-modal');
    pendingDelete = null;
    if (type === 'asset') { await loadAssets(); }
    else if (type === 'income') { await loadIncome(); }
    else if (type === 'expense') { await loadExpenses(); }
    else if (type === 'transaction') { loadTransactions(); }
    loadDashboard();
  } catch (err) {
    alert(err.message);
  }
}

/* ===== MODALS ===== */
function openModal(id) {
  // Reset form if opening add mode (no existing id field value)
  if (id === 'asset-modal') {
    const assetId = document.getElementById('asset-id');
    if (!document.querySelector('#asset-modal .modal-overlay.open')) {
      // fresh open: reset if triggered from add button
    }
  }
  document.getElementById(id).classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
  document.body.style.overflow = '';
  // Reset form fields
  const modal = document.getElementById(id);
  const form = modal.querySelector('form');
  if (form) form.reset();
  const hiddenId = modal.querySelector('input[type=hidden]');
  if (hiddenId) hiddenId.value = '';
  modal.querySelectorAll('.error-msg').forEach(el => el.textContent = '');
  // Reset modal titles
  if (id === 'asset-modal') document.getElementById('asset-modal-title').textContent = '資産を追加';
  if (id === 'income-modal') {
    document.getElementById('income-modal-title').textContent = '収入源を追加';
    document.getElementById('income-annual-preview').classList.add('hidden');
  }
  if (id === 'expense-modal') document.getElementById('expense-modal-title').textContent = '費用を追加';
}

function closeModalOutside(event, id) {
  if (event.target === document.getElementById(id)) closeModal(id);
}

/* ===== SECURITY: escape HTML ===== */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ===== TRANSACTIONS ===== */
function updateTxMonthLabel() {
  document.getElementById('tx-month-label').textContent = `${currentTxYear}年${currentTxMonth}月`;
}

function changeMonth(dir) {
  currentTxMonth += dir;
  if (currentTxMonth > 12) { currentTxMonth = 1; currentTxYear++; }
  if (currentTxMonth < 1)  { currentTxMonth = 12; currentTxYear--; }
  loadTransactions();
}

function filterTx(type, el) {
  currentTxFilter = type;
  document.querySelectorAll('#page-transactions .tx-type-filter .cat-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  loadTransactions();
}

async function loadTransactions() {
  updateTxMonthLabel();
  try {
    const data = await api('GET', `/api/transactions?year=${currentTxYear}&month=${currentTxMonth}`);
    let txs = data.transactions;
    if (currentTxFilter !== 'all') txs = txs.filter(t => t.type === currentTxFilter);

    document.getElementById('tx-total-income').textContent = formatYen(data.totalIncome);
    document.getElementById('tx-total-expense').textContent = formatYen(data.totalExpense);
    const bal = document.getElementById('tx-balance');
    bal.textContent = formatYen(data.balance);
    bal.style.color = data.balance >= 0 ? '#1565c0' : '#c62828';

    const list = document.getElementById('transactions-list');
    if (!txs.length) {
      list.innerHTML = `<div class="empty-state"><div class="empty-icon">📒</div><p>この月の記録がありません。「＋ 記録を追加」から入力してください。</p></div>`;
      return;
    }

    // Group by date
    const grouped = {};
    txs.forEach(t => {
      if (!grouped[t.date]) grouped[t.date] = [];
      grouped[t.date].push(t);
    });

    list.innerHTML = Object.keys(grouped).sort((a,b) => b.localeCompare(a)).map(date => {
      const dayTxs = grouped[date];
      const dayIncome = dayTxs.filter(t=>t.type==='income').reduce((s,t)=>s+t.amount,0);
      const dayExpense = dayTxs.filter(t=>t.type==='expense').reduce((s,t)=>s+t.amount,0);
      return `
        <div class="date-group-header">
          <span>${formatDate(date)}</span>
          <span class="day-summary">${dayIncome > 0 ? '<span class="inc">+'+formatYen(dayIncome)+'</span>' : ''}${dayExpense > 0 ? '<span class="exp">-'+formatYen(dayExpense)+'</span>' : ''}</span>
        </div>
        ${dayTxs.map(t => {
          const isIncome = t.type === 'income';
          const labels = isIncome ? TX_INCOME_CATEGORIES : TX_EXPENSE_CATEGORIES;
          const icons = isIncome ? TX_INCOME_ICONS : TX_EXPENSE_ICONS;
          return `
          <div class="item-card tx-card ${isIncome ? 'income-card' : 'expense-card'}">
            <div class="item-icon">${icons[t.category] || '💴'}</div>
            <div class="item-info">
              <div class="item-name">${escHtml(t.description || labels[t.category] || t.category)}</div>
              <div class="item-meta">${labels[t.category] || t.category}</div>
            </div>
            <div class="${isIncome ? 'tx-amount-income' : 'tx-amount-expense'}">${isIncome ? '+' : '-'}${formatYen(t.amount)}</div>
            <div class="item-actions">
              <button class="btn btn-ghost btn-icon" onclick="openEditTransaction(${t.id})">編集</button>
              <button class="btn btn-danger btn-icon" onclick="openDelete('transaction', ${t.id})">削除</button>
            </div>
          </div>`;
        }).join('')}`;
    }).join('');
  } catch(e) { console.error(e); }
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const days = ['日','月','火','水','木','金','土'];
  return `${d.getMonth()+1}月${d.getDate()}日（${days[d.getDay()]}）`;
}

function setTxType(type) {
  currentTxType = type;
  document.getElementById('tx-type').value = type;
  document.getElementById('tx-type-income').classList.toggle('active', type === 'income');
  document.getElementById('tx-type-expense').classList.toggle('active', type === 'expense');
  document.getElementById('tx-type-income').classList.toggle('income-active', type === 'income');
  document.getElementById('tx-type-expense').classList.toggle('expense-active', type === 'expense');
  updateTxCategoryOptions(type);
}

function updateTxCategoryOptions(type) {
  const cats = type === 'income' ? TX_INCOME_CATEGORIES : TX_EXPENSE_CATEGORIES;
  const sel = document.getElementById('tx-category');
  sel.innerHTML = '<option value="">選択してください</option>' +
    Object.entries(cats).map(([v, l]) => `<option value="${v}">${l}</option>`).join('');
}

function resetTransactionModal() {
  setTxType('income');
  document.getElementById('tx-date').value = new Date().toISOString().split('T')[0];
  document.getElementById('tx-id').value = '';
  document.getElementById('transaction-modal-title').textContent = '収支を記録';
}

function openEditTransaction(id) {
  const t = allTransactions.find(x => x.id === id);
  if (!t) {
    api('GET', `/api/transactions?year=${currentTxYear}&month=${currentTxMonth}`)
      .then(data => {
        const tx = data.transactions.find(x => x.id === id);
        if (tx) populateTransactionModal(tx);
      });
    return;
  }
  populateTransactionModal(t);
}

function populateTransactionModal(t) {
  document.getElementById('transaction-modal-title').textContent = '収支を編集';
  document.getElementById('tx-id').value = t.id;
  setTxType(t.type);
  document.getElementById('tx-category').value = t.category;
  document.getElementById('tx-amount').value = t.amount;
  document.getElementById('tx-date').value = t.date;
  document.getElementById('tx-description').value = t.description || '';
  document.getElementById('tx-error').textContent = '';
  openModal('transaction-modal');
}

async function handleTransactionSubmit(e) {
  e.preventDefault();
  const id = document.getElementById('tx-id').value;
  const body = {
    type: document.getElementById('tx-type').value,
    category: document.getElementById('tx-category').value,
    amount: document.getElementById('tx-amount').value,
    date: document.getElementById('tx-date').value,
    description: document.getElementById('tx-description').value
  };
  const errorEl = document.getElementById('tx-error');
  try {
    if (id) {
      await api('PUT', `/api/transactions/${id}`, body);
    } else {
      await api('POST', '/api/transactions', body);
    }
    closeModal('transaction-modal');
    loadTransactions();
  } catch(err) {
    errorEl.textContent = err.message;
  }
}

/* ===== EVENT LISTENERS ===== */
document.getElementById('income-amount').addEventListener('input', updateAnnualPreview);
document.getElementById('income-frequency').addEventListener('change', updateAnnualPreview);

/* ===== INIT ===== */
checkAuth();
