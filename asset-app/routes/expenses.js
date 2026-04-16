const express = require('express');
const router = express.Router();
const db = require('../db');

function auth(req, res, next) {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });
  next();
}

router.get('/', auth, (req, res) => {
  const rows = db.prepare('SELECT * FROM expenses WHERE user_id = ? ORDER BY category, name').all(req.session.userId);
  res.json(rows);
});

router.post('/', auth, (req, res) => {
  const { name, amount, category, notes } = req.body;
  if (!name || amount === undefined || !category) {
    return res.status(400).json({ error: '必須項目を入力してください' });
  }
  const valid = ['subscription', 'savings', 'self_defense'];
  if (!valid.includes(category)) return res.status(400).json({ error: '無効なカテゴリです' });
  try {
    const result = db.prepare(
      'INSERT INTO expenses (user_id, name, amount, category, notes) VALUES (?, ?, ?, ?, ?)'
    ).run(req.session.userId, name, parseFloat(amount) || 0, category, notes || '');
    const row = db.prepare('SELECT * FROM expenses WHERE id = ?').get(result.lastInsertRowid);
    res.json(row);
  } catch (e) {
    res.status(500).json({ error: 'サーバーエラーが発生しました' });
  }
});

router.put('/:id', auth, (req, res) => {
  const { name, amount, category, notes } = req.body;
  const existing = db.prepare('SELECT * FROM expenses WHERE id = ? AND user_id = ?').get(req.params.id, req.session.userId);
  if (!existing) return res.status(404).json({ error: '費用が見つかりません' });
  db.prepare(
    'UPDATE expenses SET name=?, amount=?, category=?, notes=? WHERE id=?'
  ).run(name || existing.name, parseFloat(amount) ?? existing.amount, category || existing.category, notes ?? existing.notes, req.params.id);
  const updated = db.prepare('SELECT * FROM expenses WHERE id = ?').get(req.params.id);
  res.json(updated);
});

router.delete('/:id', auth, (req, res) => {
  const existing = db.prepare('SELECT * FROM expenses WHERE id = ? AND user_id = ?').get(req.params.id, req.session.userId);
  if (!existing) return res.status(404).json({ error: '費用が見つかりません' });
  db.prepare('DELETE FROM expenses WHERE id = ?').run(req.params.id);
  res.json({ success: true });
});

module.exports = router;
