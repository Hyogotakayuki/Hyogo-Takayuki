const express = require('express');
const router = express.Router();
const db = require('../db');

function auth(req, res, next) {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });
  next();
}

// Get all assets
router.get('/', auth, (req, res) => {
  const assets = db.prepare('SELECT * FROM assets WHERE user_id = ? ORDER BY category, name').all(req.session.userId);
  res.json(assets);
});

// Create asset
router.post('/', auth, (req, res) => {
  const { category, name, amount, notes } = req.body;
  if (!category || !name || amount === undefined) {
    return res.status(400).json({ error: '必須項目を入力してください' });
  }
  const valid = ['bank', 'stocks', 'insurance', 'pension'];
  if (!valid.includes(category)) return res.status(400).json({ error: '無効なカテゴリです' });
  try {
    const stmt = db.prepare(
      'INSERT INTO assets (user_id, category, name, amount, notes) VALUES (?, ?, ?, ?, ?)'
    );
    const result = stmt.run(req.session.userId, category, name, parseFloat(amount) || 0, notes || '');
    const asset = db.prepare('SELECT * FROM assets WHERE id = ?').get(result.lastInsertRowid);
    res.json(asset);
  } catch (e) {
    res.status(500).json({ error: 'サーバーエラーが発生しました' });
  }
});

// Update asset
router.put('/:id', auth, (req, res) => {
  const { category, name, amount, notes } = req.body;
  const existing = db.prepare('SELECT * FROM assets WHERE id = ? AND user_id = ?').get(req.params.id, req.session.userId);
  if (!existing) return res.status(404).json({ error: '資産が見つかりません' });
  db.prepare(
    'UPDATE assets SET category=?, name=?, amount=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(category || existing.category, name || existing.name, parseFloat(amount) ?? existing.amount, notes ?? existing.notes, req.params.id);
  const updated = db.prepare('SELECT * FROM assets WHERE id = ?').get(req.params.id);
  res.json(updated);
});

// Delete asset
router.delete('/:id', auth, (req, res) => {
  const existing = db.prepare('SELECT * FROM assets WHERE id = ? AND user_id = ?').get(req.params.id, req.session.userId);
  if (!existing) return res.status(404).json({ error: '資産が見つかりません' });
  db.prepare('DELETE FROM assets WHERE id = ?').run(req.params.id);
  res.json({ success: true });
});

module.exports = router;
