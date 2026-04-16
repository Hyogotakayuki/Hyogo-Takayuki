const express = require('express');
const session = require('express-session');
const path = require('path');
const store = require('./store');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

app.use(session({
  secret: process.env.SESSION_SECRET || 'asset-mgmt-secret-2024',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: false, maxAge: 7 * 24 * 60 * 60 * 1000 }
}));

app.use('/api/auth', require('./routes/auth'));
app.use('/api/assets', require('./routes/assets'));
app.use('/api/income', require('./routes/income'));
app.use('/api/expenses', require('./routes/expenses'));

app.get('/api/dashboard', (req, res) => {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });

  const data = store.read();
  const userId = req.session.userId;

  const myAssets = data.assets.filter(a => a.user_id === userId);
  const totalAssets = myAssets.reduce((s, a) => s + a.amount, 0);

  const assetsByCategory = ['bank', 'stocks', 'insurance', 'pension'].map(cat => ({
    category: cat,
    total: myAssets.filter(a => a.category === cat).reduce((s, a) => s + a.amount, 0)
  })).filter(c => c.total > 0);

  const FREQ_MULT = { monthly: 12, bimonthly: 6, quarterly: 4, annual: 1 };
  const myIncome = data.income_sources.filter(i => i.user_id === userId);
  const annualIncome = myIncome.reduce((s, i) => s + i.amount * (FREQ_MULT[i.frequency] || 12), 0);

  const myExpenses = data.expenses.filter(e => e.user_id === userId);
  const monthlyExpenses = myExpenses.reduce((s, e) => s + e.amount, 0);

  const expensesByCategory = ['subscription', 'savings', 'self_defense'].map(cat => ({
    category: cat,
    total: myExpenses.filter(e => e.category === cat).reduce((s, e) => s + e.amount, 0)
  })).filter(c => c.total > 0);

  const healthScore = annualIncome > 0 ? totalAssets / annualIncome : null;
  let healthLabel = '未計算', healthColor = '#9e9e9e';
  if (healthScore !== null) {
    if (healthScore < 1)      { healthLabel = '要注意'; healthColor = '#f44336'; }
    else if (healthScore < 3) { healthLabel = '標準';   healthColor = '#ff9800'; }
    else if (healthScore < 5) { healthLabel = '良好';   healthColor = '#4caf50'; }
    else                      { healthLabel = '優秀';   healthColor = '#2196f3'; }
  }

  res.json({ totalAssets, annualIncome, monthlyExpenses, healthScore, healthLabel, healthColor, assetsByCategory, expensesByCategory });
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`資産管理アプリ起動中: http://localhost:${PORT}`);
});
