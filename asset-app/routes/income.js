const express = require('express');
const router = express.Router();
const store = require('../store');

function auth(req, res, next) {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });
  next();
}

const FREQ_MULT = { monthly: 12, bimonthly: 6, quarterly: 4, annual: 1 };

router.get('/', auth, (req, res) => {
  const data = store.read();
  const rows = data.income_sources
    .filter(i => i.user_id === req.session.userId)
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(i => ({ ...i, annual: i.amount * (FREQ_MULT[i.frequency] || 12) }));
  res.json(rows);
});

router.post('/', auth, (req, res) => {
  const { name, amount, frequency, notes } = req.body;
  if (!name || amount === undefined || !frequency)
    return res.status(400).json({ error: '必須項目を入力してください' });
  if (!FREQ_MULT[frequency])
    return res.status(400).json({ error: '無効な頻度です' });

  const data = store.read();
  const item = {
    id: store.nextId(data.income_sources),
    user_id: req.session.userId,
    name,
    amount: parseFloat(amount) || 0,
    frequency,
    notes: notes || '',
    created_at: new Date().toISOString()
  };
  data.income_sources.push(item);
  store.write(data);
  res.json({ ...item, annual: item.amount * FREQ_MULT[item.frequency] });
});

router.put('/:id', auth, (req, res) => {
  const id = parseInt(req.params.id);
  const data = store.read();
  const idx = data.income_sources.findIndex(i => i.id === id && i.user_id === req.session.userId);
  if (idx === -1) return res.status(404).json({ error: '収入源が見つかりません' });

  const { name, amount, frequency, notes } = req.body;
  const newFreq = frequency || data.income_sources[idx].frequency;
  if (!FREQ_MULT[newFreq]) return res.status(400).json({ error: '無効な頻度です' });

  data.income_sources[idx] = {
    ...data.income_sources[idx],
    name: name || data.income_sources[idx].name,
    amount: amount !== undefined ? parseFloat(amount) : data.income_sources[idx].amount,
    frequency: newFreq,
    notes: notes !== undefined ? notes : data.income_sources[idx].notes
  };
  store.write(data);
  const updated = data.income_sources[idx];
  res.json({ ...updated, annual: updated.amount * FREQ_MULT[updated.frequency] });
});

router.delete('/:id', auth, (req, res) => {
  const id = parseInt(req.params.id);
  const data = store.read();
  const idx = data.income_sources.findIndex(i => i.id === id && i.user_id === req.session.userId);
  if (idx === -1) return res.status(404).json({ error: '収入源が見つかりません' });
  data.income_sources.splice(idx, 1);
  store.write(data);
  res.json({ success: true });
});

module.exports = router;
