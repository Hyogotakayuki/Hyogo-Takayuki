const express = require('express');
const router = express.Router();
const store = require('../store');

function auth(req, res, next) {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });
  next();
}

const VALID_TYPES = ['income', 'expense'];
const INCOME_CATEGORIES = ['salary', 'business', 'investment', 'pension', 'other_income'];
const EXPENSE_CATEGORIES = ['food', 'utilities', 'subscription', 'socializing', 'hygiene', 'stress_relief', 'enrichment', 'medical', 'transport', 'clothing', 'other'];

function getMonthlyStats(transactions, userId) {
  const now = new Date();
  const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  const monthly = transactions.filter(t => t.user_id === userId && t.date.startsWith(ym));
  const income = monthly.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0);
  const expense = monthly.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0);
  return { income, expense, balance: income - expense };
}

// GET transactions (with optional filters)
router.get('/', auth, (req, res) => {
  const data = store.read();
  if (!data.transactions) data.transactions = [];
  let txs = data.transactions.filter(t => t.user_id === req.session.userId);

  const { year, month, type } = req.query;
  if (year && month) {
    const ym = `${year}-${String(month).padStart(2, '0')}`;
    txs = txs.filter(t => t.date.startsWith(ym));
  }
  if (type) txs = txs.filter(t => t.type === type);

  txs.sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id);

  const totalIncome = txs.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0);
  const totalExpense = txs.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0);
  const monthly = getMonthlyStats(data.transactions, req.session.userId);

  res.json({ transactions: txs, totalIncome, totalExpense, balance: totalIncome - totalExpense, monthly });
});

// POST transaction
router.post('/', auth, (req, res) => {
  const { type, category, amount, description, date } = req.body;
  if (!type || !category || amount === undefined || !date)
    return res.status(400).json({ error: '必須項目を入力してください' });
  if (!VALID_TYPES.includes(type))
    return res.status(400).json({ error: '無効な種別です' });

  const data = store.read();
  if (!data.transactions) data.transactions = [];

  const tx = {
    id: store.nextId(data.transactions),
    user_id: req.session.userId,
    type,
    category,
    amount: parseFloat(amount) || 0,
    description: description || '',
    date,
    created_at: new Date().toISOString()
  };
  data.transactions.push(tx);
  store.write(data);
  res.json(tx);
});

// PUT transaction
router.put('/:id', auth, (req, res) => {
  const id = parseInt(req.params.id);
  const data = store.read();
  if (!data.transactions) data.transactions = [];
  const idx = data.transactions.findIndex(t => t.id === id && t.user_id === req.session.userId);
  if (idx === -1) return res.status(404).json({ error: '取引が見つかりません' });

  const { type, category, amount, description, date } = req.body;
  data.transactions[idx] = {
    ...data.transactions[idx],
    type: type || data.transactions[idx].type,
    category: category || data.transactions[idx].category,
    amount: amount !== undefined ? parseFloat(amount) : data.transactions[idx].amount,
    description: description !== undefined ? description : data.transactions[idx].description,
    date: date || data.transactions[idx].date
  };
  store.write(data);
  res.json(data.transactions[idx]);
});

// DELETE transaction
router.delete('/:id', auth, (req, res) => {
  const id = parseInt(req.params.id);
  const data = store.read();
  if (!data.transactions) data.transactions = [];
  const idx = data.transactions.findIndex(t => t.id === id && t.user_id === req.session.userId);
  if (idx === -1) return res.status(404).json({ error: '取引が見つかりません' });
  data.transactions.splice(idx, 1);
  store.write(data);
  res.json({ success: true });
});

// GET monthly summary by category
router.get('/summary', auth, (req, res) => {
  const data = store.read();
  if (!data.transactions) data.transactions = [];
  const { year, month } = req.query;
  const ym = year && month
    ? `${year}-${String(month).padStart(2, '0')}`
    : (() => { const n = new Date(); return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,'0')}`; })();

  const txs = data.transactions.filter(t => t.user_id === req.session.userId && t.date.startsWith(ym));
  const byCat = {};
  txs.forEach(t => {
    const key = `${t.type}:${t.category}`;
    byCat[key] = (byCat[key] || 0) + t.amount;
  });
  res.json({ ym, summary: byCat });
});

module.exports = router;
