const express = require('express');
const router = express.Router();
const store = require('../store');

function auth(req, res, next) {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });
  next();
}

const VALID_CATEGORIES = ['subscription'];

router.get('/', auth, (req, res) => {
  const data = store.read();
  const rows = data.expenses
    .filter(e => e.user_id === req.session.userId)
    .sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name));
  res.json(rows);
});

router.post('/', auth, (req, res) => {
  const { name, amount, category, notes } = req.body;
  if (!name || amount === undefined || !category)
    return res.status(400).json({ error: '必須項目を入力してください' });
  if (!VALID_CATEGORIES.includes(category))
    return res.status(400).json({ error: '無効なカテゴリです' });

  const data = store.read();
  const item = {
    id: store.nextId(data.expenses),
    user_id: req.session.userId,
    name,
    amount: parseFloat(amount) || 0,
    category,
    notes: notes || '',
    created_at: new Date().toISOString()
  };
  data.expenses.push(item);
  store.write(data);
  res.json(item);
});

router.put('/:id', auth, (req, res) => {
  const id = parseInt(req.params.id);
  const data = store.read();
  const idx = data.expenses.findIndex(e => e.id === id && e.user_id === req.session.userId);
  if (idx === -1) return res.status(404).json({ error: '費用が見つかりません' });

  const { name, amount, category, notes } = req.body;
  data.expenses[idx] = {
    ...data.expenses[idx],
    name: name || data.expenses[idx].name,
    amount: amount !== undefined ? parseFloat(amount) : data.expenses[idx].amount,
    category: category || data.expenses[idx].category,
    notes: notes !== undefined ? notes : data.expenses[idx].notes
  };
  store.write(data);
  res.json(data.expenses[idx]);
});

router.delete('/:id', auth, (req, res) => {
  const id = parseInt(req.params.id);
  const data = store.read();
  const idx = data.expenses.findIndex(e => e.id === id && e.user_id === req.session.userId);
  if (idx === -1) return res.status(404).json({ error: '費用が見つかりません' });
  data.expenses.splice(idx, 1);
  store.write(data);
  res.json({ success: true });
});

module.exports = router;
