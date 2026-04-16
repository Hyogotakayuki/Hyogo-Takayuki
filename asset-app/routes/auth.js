const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const store = require('../store');

router.post('/register', (req, res) => {
  const { username, email, password } = req.body;
  if (!username || !email || !password)
    return res.status(400).json({ error: '全項目を入力してください' });
  if (password.length < 6)
    return res.status(400).json({ error: 'パスワードは6文字以上必要です' });

  const data = store.read();
  if (data.users.find(u => u.username === username))
    return res.status(409).json({ error: 'このユーザー名は既に使用されています' });
  if (data.users.find(u => u.email === email))
    return res.status(409).json({ error: 'このメールアドレスは既に使用されています' });

  const user = {
    id: store.nextId(data.users),
    username,
    email,
    password_hash: bcrypt.hashSync(password, 10),
    created_at: new Date().toISOString()
  };
  data.users.push(user);
  store.write(data);

  req.session.userId = user.id;
  req.session.username = user.username;
  res.json({ success: true, username });
});

router.post('/login', (req, res) => {
  const { email, password } = req.body;
  if (!email || !password)
    return res.status(400).json({ error: 'メールアドレスとパスワードを入力してください' });

  const data = store.read();
  const user = data.users.find(u => u.email === email);
  if (!user || !bcrypt.compareSync(password, user.password_hash))
    return res.status(401).json({ error: 'メールアドレスまたはパスワードが正しくありません' });

  req.session.userId = user.id;
  req.session.username = user.username;
  res.json({ success: true, username: user.username });
});

router.post('/logout', (req, res) => {
  req.session.destroy(() => res.json({ success: true }));
});

router.get('/me', (req, res) => {
  if (req.session.userId) {
    res.json({ loggedIn: true, username: req.session.username });
  } else {
    res.json({ loggedIn: false });
  }
});

module.exports = router;
