const express = require('express');
const session = require('express-session');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Session store using SQLite
const SQLiteStore = require('connect-sqlite3')(session);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

app.use(session({
  store: new SQLiteStore({ db: 'sessions.db', dir: path.join(__dirname, 'data') }),
  secret: process.env.SESSION_SECRET || 'asset-mgmt-secret-2024',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: false, maxAge: 7 * 24 * 60 * 60 * 1000 } // 7 days
}));

// Routes
app.use('/api/auth', require('./routes/auth'));
app.use('/api/assets', require('./routes/assets'));
app.use('/api/income', require('./routes/income'));
app.use('/api/expenses', require('./routes/expenses'));

// Dashboard summary endpoint
app.get('/api/dashboard', (req, res) => {
  if (!req.session.userId) return res.status(401).json({ error: '認証が必要です' });

  const db = require('./db');
  const userId = req.session.userId;

  const assets = db.prepare('SELECT category, SUM(amount) as total FROM assets WHERE user_id = ? GROUP BY category').all(userId);
  const totalAssets = db.prepare('SELECT COALESCE(SUM(amount), 0) as total FROM assets WHERE user_id = ?').get(userId).total;

  const incomes = db.prepare('SELECT amount, frequency FROM income_sources WHERE user_id = ?').all(userId);
  const freqMultiplier = { monthly: 12, bimonthly: 6, quarterly: 4, annual: 1 };
  const annualIncome = incomes.reduce((sum, i) => sum + i.amount * (freqMultiplier[i.frequency] || 12), 0);

  const expenses = db.prepare('SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category').all(userId);
  const monthlyExpenses = db.prepare('SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = ?').get(userId).total;

  const healthScore = annualIncome > 0 ? totalAssets / annualIncome : null;

  let healthLabel = '未計算';
  let healthColor = '#9e9e9e';
  if (healthScore !== null) {
    if (healthScore < 1) { healthLabel = '要注意'; healthColor = '#f44336'; }
    else if (healthScore < 3) { healthLabel = '標準'; healthColor = '#ff9800'; }
    else if (healthScore < 5) { healthLabel = '良好'; healthColor = '#4caf50'; }
    else { healthLabel = '優秀'; healthColor = '#2196f3'; }
  }

  res.json({
    totalAssets,
    annualIncome,
    monthlyExpenses,
    healthScore,
    healthLabel,
    healthColor,
    assetsByCategory: assets,
    expensesByCategory: expenses
  });
});

// Catch-all: serve index.html for SPA
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`資産管理アプリ起動中: http://localhost:${PORT}`);
});
