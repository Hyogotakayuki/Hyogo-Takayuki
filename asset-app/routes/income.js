const express = require('express');
const router = express.Router();
const db = require('../db');

function auth(req, res, next) {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });
  next();
}

const FREQ_MULT = { monthly: 12, bimonthly: 6, quarterly: 4, annual: 1 };

router.get('/', auth, (req, res) => {
  const rows = db.prepare('SELECT * FROM income_sources WHERE user_id = ? ORDER BY name').all(req.session.userId);
  const withAnnual = rows.map(r => ({ ...r, annual: r.amount * (FREQ_MULT[r.frequency] || 12) }));
  res.json(withAnnual);
});

router.post('/', auth, (req, res) => {
  const { name, amount, frequency, notes } = req.body;
  if (!name || amount === undefined || !frequency) {
    return res.status(400).json({ error: '必須項目を入力してください' });
  }
  if (!FREQ_MULT[frequency]) return res.status(400).json({ error: '無効な頻度です' });
  try {
    const result = db.prepare(
      'INSERT INTO income_sources (user_id, name, amount, frequency, notes) VALUES (?, ?, ?, ?, ?)'
    ).run(req.session.userId, name, parseFloat(amount) || 0, frequency, notes || '');
    const row = db.prepare('SELECT * FROM income_sources WHERE id = ?').get(result.lastInsertRowid);
    res.json({ ...row, annual: row.amount * FREQ_MULT[row.frequency] });
  } catch (e) {
    res.status(500).json({ error: 'サーバーエラーが発生しました' });
  }
});

router.put('/:id', auth, (req, res) => {
  const { name, amount, frequency, notes } = req.body;
  const existing = db.prepare('SELECT * FROM income_sources WHERE id = ? AND user_id = ?').get(req.params.id, req.session.userId);
  if (!existing) return res.status(404).json({ error: '収入源が見つかりません' });
  const newFreq = frequency || existing.frequency;
  if (!FREQ_MULT[newFreq]) return res.status(400).json({ error: '無効な頻度です' });
  db.prepare(
    'UPDATE income_sources SET name=?, amount=?, frequency=?, notes=? WHERE id=?'
  ).run(name || existing.name, parseFloat(amount) ?? existing.amount, newFreq, notes ?? existing.notes, req.params.id);
  const updated = db.prepare('SELECT * FROM income_sources WHERE id = ?').get(req.params.id);
  res.json({ ...updated, annual: updated.amount * FREQ_MULT[updated.frequency] });
});

router.delete('/:id', auth, (req, res) => {
  const existing = db.prepare('SELECT * FROM income_sources WHERE id = ? AND user_id = ?').get(req.params.id, req.session.userId);
  if (!existing) return res.status(404).json({ error: '収入源が見つかりません' });
  db.prepare('DELETE FROM income_sources WHERE id = ?').run(req.params.id);
  res.json({ success: true });
});

module.exports = router;
