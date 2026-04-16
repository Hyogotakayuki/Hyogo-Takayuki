const express = require('express');
const router = express.Router();
const store = require('../store');

function auth(req, res, next) {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });
  next();
}

const VALID_CATEGORIES = ['bank', 'stocks', 'insurance', 'pension', 'savings', 'self_defense'];

router.get('/', auth, (req, res) => {
  const data = store.read();
  const assets = data.assets
    .filter(a => a.user_id === req.session.userId)
    .sort((a, b) => a.category.localeCompare(b.category) || a.name.localeCompare(b.name));
  res.json(assets);
});

router.post('/', auth, (req, res) => {
  const { category, name, amount, notes } = req.body;
  if (!category || !name || amount === undefined)
    return res.status(400).json({ error: '必須項目を入力してください' });
  if (!VALID_CATEGORIES.includes(category))
    return res.status(400).json({ error: '無効なカテゴリです' });

  const data = store.read();
  const asset = {
    id: store.nextId(data.assets),
    user_id: req.session.userId,
    category,
    name,
    amount: parseFloat(amount) || 0,
    notes: notes || '',
    updated_at: new Date().toISOString()
  };
  data.assets.push(asset);
  store.write(data);
  res.json(asset);
});

router.put('/:id', auth, (req, res) => {
  const id = parseInt(req.params.id);
  const data = store.read();
  const idx = data.assets.findIndex(a => a.id === id && a.user_id === req.session.userId);
  if (idx === -1) return res.status(404).json({ error: '資産が見つかりません' });

  const { category, name, amount, notes } = req.body;
  data.assets[idx] = {
    ...data.assets[idx],
    category: category || data.assets[idx].category,
    name: name || data.assets[idx].name,
    amount: amount !== undefined ? parseFloat(amount) : data.assets[idx].amount,
    notes: notes !== undefined ? notes : data.assets[idx].notes,
    updated_at: new Date().toISOString()
  };
  store.write(data);
  res.json(data.assets[idx]);
});

router.delete('/:id', auth, (req, res) => {
  const id = parseInt(req.params.id);
  const data = store.read();
  const idx = data.assets.findIndex(a => a.id === id && a.user_id === req.session.userId);
  if (idx === -1) return res.status(404).json({ error: '資産が見つかりません' });
  data.assets.splice(idx, 1);
  store.write(data);
  res.json({ success: true });
});

module.exports = router;
